"""
Tests for VirtualBot.

Key design note: both process_update() and process_new_token() call
_scan_for_entry(), which can update active_positions. Tests drive
entries/exits through whichever path is most direct.

ShadowRecorder writes to disk on init, so it is always mocked.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.pulse.types import (
    SharedTokenState, SellReason, SellCategory
)
from src.pulse.trading.fleet.virtual_bot import VirtualBot
from __tests__.conftest import make_token, make_config, make_past_trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_recorder():
    """Return a MagicMock that satisfies VirtualBot's recorder usage."""
    recorder = MagicMock()
    recorder.log_trade = MagicMock()
    return recorder


def make_bot(sol_price: float = 150.0, **config_overrides) -> VirtualBot:
    """VirtualBot with a mocked recorder and a strategy that can signal buys."""
    defaults = dict(
        # Ensure tokens pass all strategy gates at sol_price=150
        baseline_confidence_score=60.0,  # above min=50 → always confident
        min_confidence_score=50.0,
        good_confidence_score=70.0,
        stop_loss_pct=0.30,
        take_profit_pct=0.60,
        max_holding_time=300,
        max_trades_per_token=3,
        cooldown_minutes=3,
        fees_percentage=0.03,
    )
    defaults.update(config_overrides)  # overrides win
    config = make_config(**defaults)
    bot = VirtualBot("TEST", config, make_recorder())
    bot._current_sol_price = sol_price
    return bot


def make_shared(token=None, holders=None, snapshots=None, ath=0.0) -> SharedTokenState:
    """Build a SharedTokenState suitable for process_update / process_new_token."""
    if token is None:
        token = make_token()
    state = SharedTokenState(
        token=token,
        ath_market_cap=ath,
        snapshots=snapshots or [],
        raw_holders=holders,
    )
    return state


# ---------------------------------------------------------------------------
# Buy entry
# ---------------------------------------------------------------------------

def test_buy_creates_active_position():
    """process_update with a valid finalStretch token → position opened."""
    bot = make_bot()
    shared = make_shared(ath=12000.0)
    bot.process_update(shared, sol_price=150.0)
    assert shared.token.pair_address in bot.active_positions


def test_no_buy_when_sol_price_zero():
    """_scan_for_entry exits early if sol_price = 0."""
    bot = make_bot(sol_price=0.0)
    shared = make_shared()
    bot.process_update(shared, sol_price=0.0)
    assert shared.token.pair_address not in bot.active_positions


def test_no_buy_wrong_category():
    """Token not in finalStretch → should_buy returns False."""
    bot = make_bot()
    token = make_token(category="newPairs")
    shared = make_shared(token=token)
    bot.process_update(shared, sol_price=150.0)
    assert token.pair_address not in bot.active_positions


def test_process_new_token_also_triggers_entry():
    """process_new_token (with raw_holders) also calls _scan_for_entry."""
    bot = make_bot()
    # Provide minimal holders so safety score is calculated
    holders = [["lp", 5.0, 999.0]] + [[f"h{i}", 1.0, 5.0] for i in range(10)]
    shared = make_shared(holders=holders, ath=12000.0)
    bot.process_new_token(shared)
    assert shared.token.pair_address in bot.active_positions


# ---------------------------------------------------------------------------
# Trade limits respected
# ---------------------------------------------------------------------------

def test_max_trades_per_token_respected():
    """After max_trades_per_token past trades, no new buy."""
    bot = make_bot(max_trades_per_token=3)
    token = make_token()
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=600) for _ in range(3)]
    bot.past_trades[token.pair_address] = past
    shared = make_shared(token=token, ath=12000.0)
    bot.process_update(shared, sol_price=150.0)
    assert token.pair_address not in bot.active_positions


def test_cooldown_blocks_reentry():
    """Sold 60s ago with cooldown=3min → new buy blocked."""
    bot = make_bot(cooldown_minutes=3)
    token = make_token()
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=60)]
    bot.past_trades[token.pair_address] = past
    shared = make_shared(token=token, ath=12000.0)
    bot.process_update(shared, sol_price=150.0)
    assert token.pair_address not in bot.active_positions


def test_cooldown_expired_allows_reentry():
    """Sold 200s ago with cooldown=3min (180s) → buy allowed."""
    bot = make_bot(cooldown_minutes=3)
    token = make_token()
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=200)]
    bot.past_trades[token.pair_address] = past
    shared = make_shared(token=token, ath=12000.0)
    bot.process_update(shared, sol_price=150.0)
    assert token.pair_address in bot.active_positions


# ---------------------------------------------------------------------------
# Sell / position lifecycle
# ---------------------------------------------------------------------------

def _open_position(bot: VirtualBot, token, buy_mc: float, seconds_held: int = 10):
    """Directly inject an active position, bypassing should_buy."""
    from src.pulse.types import TradeTakenInformation
    trade = TradeTakenInformation(
        token_bought_snapshot=token,
        buy_market_cap=buy_mc,
        current_market_cap=buy_mc,
        time_bought=datetime.now(timezone.utc) - timedelta(seconds=seconds_held),
        position_size=1.0,
        confidence=50.0,
    )
    bot.active_positions[token.pair_address] = trade
    bot._current_sol_price = buy_mc / token.market_cap  # back-calculate so MC matches


def test_stop_loss_clears_active_position():
    """MC drops below SL threshold → position removed, added to past_trades."""
    bot = make_bot(stop_loss_pct=0.30)
    buy_sol_price = 150.0
    buy_mc = 12000.0  # USD
    # Token with MC that dropped 40% → below SL (30%)
    exit_mc_usd = buy_mc * 0.60
    token = make_token(market_cap=exit_mc_usd / buy_sol_price)
    _open_position(bot, token, buy_mc)
    bot._current_sol_price = buy_sol_price

    shared = make_shared(token=token)
    bot.process_update(shared, sol_price=buy_sol_price)

    assert token.pair_address not in bot.active_positions
    assert token.pair_address in bot.past_trades
    assert bot.past_trades[token.pair_address][-1].sell_reason.category == SellCategory.STOP_LOSS


def test_take_profit_clears_active_position():
    """MC rises above TP threshold → position removed, added to past_trades."""
    bot = make_bot(take_profit_pct=0.60)
    buy_sol_price = 150.0
    buy_mc = 12000.0
    # Token with MC that rose 70% → above TP (60%)
    exit_mc_usd = buy_mc * 1.70
    token = make_token(market_cap=exit_mc_usd / buy_sol_price)
    _open_position(bot, token, buy_mc)
    bot._current_sol_price = buy_sol_price

    shared = make_shared(token=token)
    bot.process_update(shared, sol_price=buy_sol_price)

    assert token.pair_address not in bot.active_positions
    assert bot.past_trades[token.pair_address][-1].sell_reason.category == SellCategory.TAKE_PROFIT


def test_no_sell_within_limits():
    """MC within SL/TP band, time within limit → position stays open."""
    bot = make_bot(stop_loss_pct=0.30, take_profit_pct=0.60)
    buy_sol_price = 150.0
    buy_mc = 12000.0
    # MC unchanged → well within band
    token = make_token(market_cap=buy_mc / buy_sol_price)
    _open_position(bot, token, buy_mc, seconds_held=10)
    bot._current_sol_price = buy_sol_price

    shared = make_shared(token=token)
    bot.process_update(shared, sol_price=buy_sol_price)

    assert token.pair_address in bot.active_positions


# ---------------------------------------------------------------------------
# PnL calculation
# ---------------------------------------------------------------------------


def test_pnl_calculation_profitable():
    """
    entry_mc=12_000, exit_mc=18_000 (50% up), position=1.0 SOL, fees=3%.
    buy_fees = 0.03, initial_cost = 1.03
    value_ratio = 18000/12000 = 1.5
    gross_exit = 1.5, sell_fees = 0.045, net_exit = 1.455
    net_profit = 1.455 - 1.03 = 0.425
    """
    bot = make_bot(fees_percentage=0.03)
    sol_price = 150.0
    buy_mc = 12000.0
    token = make_token(market_cap=buy_mc / sol_price)
    _open_position(bot, token, buy_mc)

    # Move price up 50%
    exit_sol_price = sol_price * 1.5
    exit_mc_usd = token.market_cap * exit_sol_price
    bot._current_sol_price = exit_sol_price
    trade = bot.active_positions[token.pair_address]._replace(current_market_cap=exit_mc_usd)
    bot.active_positions[token.pair_address] = trade
    bot._execute_virtual_sell(trade, SellReason(category=SellCategory.TAKE_PROFIT))

    result = bot.past_trades[token.pair_address][-1]
    expected_profit = pytest.approx(0.425, rel=1e-3)
    assert result.profit == expected_profit


def test_pnl_calculation_loss():
    """
    entry_mc=12_000, exit_mc=8_400 (30% down), position=1.0 SOL, fees=3%.
    value_ratio = 0.7, gross_exit = 0.7, sell_fees = 0.021, net_exit = 0.679
    net_profit = 0.679 - 1.03 = -0.351
    """
    bot = make_bot(fees_percentage=0.03)
    sol_price = 150.0
    buy_mc = 12000.0
    token = make_token(market_cap=buy_mc / sol_price)
    _open_position(bot, token, buy_mc)

    # Move price down 30%
    exit_sol_price = sol_price * 0.70
    exit_mc_usd = token.market_cap * exit_sol_price
    bot._current_sol_price = exit_sol_price
    trade = bot.active_positions[token.pair_address]._replace(current_market_cap=exit_mc_usd)
    bot.active_positions[token.pair_address] = trade
    bot._execute_virtual_sell(trade, SellReason(category=SellCategory.STOP_LOSS))

    result = bot.past_trades[token.pair_address][-1]
    expected_profit = pytest.approx(-0.351, rel=1e-3)
    assert result.profit == expected_profit


# ---------------------------------------------------------------------------
# Safety score caching
# ---------------------------------------------------------------------------

def test_safety_score_cached_on_new_token():
    """process_new_token with rich raw_holders → holder_safety_score cached."""
    bot = make_bot()
    holders = [["lp", 5.0, 999.0]] + [[f"h{i}", 1.0, 10.0] for i in range(20)]
    token = make_token()
    shared = make_shared(token=token, holders=holders)
    bot.process_new_token(shared)
    assert token.pair_address in bot.holder_safety_score
    assert bot.holder_safety_score[token.pair_address] == pytest.approx(1.0)


def test_no_safety_score_without_holders():
    """process_new_token with no raw_holders → no score cached."""
    bot = make_bot()
    shared = make_shared(holders=None)
    bot.process_new_token(shared)
    assert shared.token.pair_address not in bot.holder_safety_score
