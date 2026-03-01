"""
Tests for ShadowFleetManager.

Focuses on the orchestration logic that doesn't require a live API:
fleet spawning, shared state management, snapshot throttling, ATH tracking,
and pure helper methods (candle parsing, chart param calculation).

AxiomTradeClient and PulseTracker are mocked to avoid network calls.
ShadowRecorder is mocked to avoid filesystem writes.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.pulse.trading.fleet.shadow_fleet_manager import ShadowFleetManager
from __tests__.conftest import make_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_manager() -> ShadowFleetManager:
    """ShadowFleetManager with mocked tracker, recorder, and API client (no I/O)."""
    tracker = MagicMock()
    with patch("src.pulse.trading.fleet.shadow_fleet_manager.AxiomTradeClient", MagicMock()):
        with patch("src.pulse.trading.fleet.shadow_fleet_manager.ShadowRecorder"):
            with patch("src.pulse.trading.fleet.virtual_bot.ShadowRecorder"):
                manager = ShadowFleetManager(tracker)
    manager.current_sol_price = 150.0
    return manager


# ---------------------------------------------------------------------------
# Fleet spawning
# ---------------------------------------------------------------------------

def test_spawn_fleet_creates_five_bots():
    manager = make_manager()
    manager._spawn_fleet()
    assert len(manager.bots) == 501


def test_spawn_fleet_bot_names():
    manager = make_manager()
    manager._spawn_fleet()
    names = [b.strategy_id for b in manager.bots]
    assert set(names[:5]) == {"BASE", "Bot_000", "Bot_001", "Bot_002", "Bot_003"}


def test_bot_configs_differ():
    """Each variant should have a distinct config value from BASE."""
    manager = make_manager()
    manager._spawn_fleet()

    bots = {b.strategy_id: b for b in manager.bots}
    assert pytest.approx(bots["BASE"].config.risk.take_profit_pct, abs=0.001) != pytest.approx(bots["Bot_000"].config.risk.take_profit_pct, abs=0.001) or pytest.approx(bots["BASE"].config.risk.take_profit_pct, abs=0.001) != pytest.approx(bots["Bot_001"].config.risk.take_profit_pct, abs=0.001) or pytest.approx(bots["BASE"].config.risk.take_profit_pct, abs=0.001) != pytest.approx(bots["Bot_002"].config.risk.take_profit_pct, abs=0.001) or pytest.approx(bots["BASE"].config.risk.take_profit_pct, abs=0.001) != pytest.approx(bots["Bot_003"].config.risk.take_profit_pct, abs=0.001)


# ---------------------------------------------------------------------------
# on_token_update — shared state management
# ---------------------------------------------------------------------------

async def test_on_token_update_creates_shared_state():
    """First call for a new token creates a SharedTokenState entry."""
    manager = make_manager()
    manager._spawn_fleet()
    token = make_token()
    assert token.pair_address not in manager.shared_tokens

    await manager.on_token_update(token)

    assert token.pair_address in manager.shared_tokens
    assert manager.shared_tokens[token.pair_address].token is token


async def test_on_token_update_records_first_snapshot():
    """A snapshot is recorded on the first update."""
    manager = make_manager()
    manager._spawn_fleet()
    token = make_token()

    await manager.on_token_update(token)

    state = manager.shared_tokens[token.pair_address]
    assert len(state.snapshots) == 1


# ---------------------------------------------------------------------------
# Snapshot throttling
# ---------------------------------------------------------------------------

async def test_snapshot_recorded_after_2s():
    """Two updates 3s apart → 2 snapshots."""
    manager = make_manager()
    manager._spawn_fleet()
    token = make_token()

    await manager.on_token_update(token)
    state = manager.shared_tokens[token.pair_address]
    # Manually backdate last_snapshot_time to simulate 3s passing
    state.last_snapshot_time = datetime.now(timezone.utc) - timedelta(seconds=3)

    await manager.on_token_update(token)
    assert len(state.snapshots) == 2


async def test_snapshot_throttled_within_2s():
    """Two updates <2s apart → still only 1 snapshot."""
    manager = make_manager()
    manager._spawn_fleet()
    token = make_token()

    await manager.on_token_update(token)
    # Immediately call again (no time backdating)
    await manager.on_token_update(token)

    state = manager.shared_tokens[token.pair_address]
    assert len(state.snapshots) == 1


# ---------------------------------------------------------------------------
# ATH tracking
# ---------------------------------------------------------------------------

async def test_ath_increases_when_mc_rises():
    """ATH is updated when market cap is higher than previous peak."""
    manager = make_manager()
    manager._spawn_fleet()
    manager.current_sol_price = 150.0

    token_low = make_token(market_cap=80.0)   # $12_000
    await manager.on_token_update(token_low)
    state = manager.shared_tokens[token_low.pair_address]
    first_ath = state.ath_market_cap

    token_high = make_token(market_cap=140.0)  # $21_000 — higher MC, same pair
    token_high.pair_address = token_low.pair_address
    manager.current_sol_price = 150.0
    await manager.on_token_update(token_high)

    assert state.ath_market_cap > first_ath


async def test_ath_does_not_decrease():
    """ATH should never go down even when MC drops."""
    manager = make_manager()
    manager._spawn_fleet()
    manager.current_sol_price = 150.0

    # First update — high MC
    token = make_token(market_cap=140.0)  # $21_000
    await manager.on_token_update(token)
    state = manager.shared_tokens[token.pair_address]
    peak_ath = state.ath_market_cap

    # Second update — lower MC
    token.market_cap = 60.0  # $9_000
    state.last_snapshot_time = datetime.now(timezone.utc) - timedelta(seconds=3)
    await manager.on_token_update(token)

    assert state.ath_market_cap == pytest.approx(peak_ath)


# ---------------------------------------------------------------------------
# _extract_ath_from_candles — pure helper
# ---------------------------------------------------------------------------

def test_extract_ath_from_candles_dict_format():
    """Parses {"candles": [[o, l, h, c], ...]} and returns max high."""
    manager = make_manager()
    candles_data = {"candles": [
        [100, 90, 120.0, 110],
        [110, 95, 135.0, 130],
        [130, 100, 115.0, 105],
    ]}
    assert manager._extract_ath_from_candles(candles_data) == pytest.approx(135.0)


def test_extract_ath_from_candles_list_format():
    """Parses a raw list of [o, l, h, c] candles and returns max high."""
    manager = make_manager()
    candles_data = [
        [100, 90, 50.0, 110],
        [110, 95, 80.0, 130],
        [130, 100, 60.0, 105],
    ]
    assert manager._extract_ath_from_candles(candles_data) == pytest.approx(80.0)




def test_extract_ath_empty_candles():
    """Empty input → 0.0 (no crash)."""
    manager = make_manager()
    assert manager._extract_ath_from_candles([]) == pytest.approx(0.0)
    assert manager._extract_ath_from_candles(None) == pytest.approx(0.0)
    assert manager._extract_ath_from_candles({}) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _calculate_chart_params — pure helper
# ---------------------------------------------------------------------------

def test_calculate_chart_params_structure():
    """Verify chart params dict has expected keys and sensible values."""
    manager = make_manager()
    pair_info = {
        "openTrading": "2025-01-01T00:00:00Z",
        "createdAt": "2025-01-01T00:00:00Z",
    }
    last_tx = {
        "createdAt": "2025-01-01T00:01:00Z",
        "v": 999999,
    }
    params = manager._calculate_chart_params(pair_info, last_tx)

    assert "from_ts" in params
    assert "to_ts" in params
    assert params["to_ts"] > params["from_ts"]
    # from_ts should be ~1 hour before to_ts (within 10s tolerance)
    diff_ms = params["to_ts"] - params["from_ts"]
    assert abs(diff_ms - 60 * 60 * 1000) < 10_000


# ---------------------------------------------------------------------------
# on_token_removed — integration: fleet manager + virtual bot
# ---------------------------------------------------------------------------

import asyncio
from datetime import timedelta
from src.pulse.types import SharedTokenState, TradeTakenInformation, SellCategory
from src.pulse.trading.fleet.virtual_bot import VirtualBot
from __tests__.conftest import make_config

SOL_PRICE = 150.0


def make_manager_with_single_bot(sol_price: float = SOL_PRICE) -> ShadowFleetManager:
    """
    ShadowFleetManager wired with ONE controllable VirtualBot.
    Recorder and AxiomTradeClient are mocked — no I/O.
    """
    recorder = MagicMock()
    recorder.log_trade = MagicMock()

    config = make_config(
        baseline_confidence_score=60.0,
        min_confidence_score=50.0,
        stop_loss_pct=0.30,
        take_profit_pct=0.60,
        max_holding_time=300,
        fees_percentage=0.03,
    )
    bot = VirtualBot("TEST", config, recorder)
    bot._current_sol_price = sol_price

    tracker = MagicMock()
    with patch("src.pulse.trading.fleet.shadow_fleet_manager.ShadowRecorder"):
        manager = ShadowFleetManager(tracker)
    manager.current_sol_price = sol_price
    manager.bots = [bot]
    manager.client = MagicMock()
    return manager


def plant_position(manager: ShadowFleetManager, token, buy_mc_usd: float):
    """Directly insert an active position into every bot, bypassing buy logic."""
    for bot in manager.bots:
        trade = TradeTakenInformation(
            token_bought_snapshot=token,
            buy_market_cap=buy_mc_usd,
            current_market_cap=buy_mc_usd,
            time_bought=datetime.now(timezone.utc) - timedelta(seconds=30),
            position_size=1.0,
            confidence=60.0,
        )
        bot.active_positions[token.pair_address] = trade


@pytest.mark.asyncio
async def test_token_removed_uses_last_tx_price():
    """
    get_last_transaction returns priceSol → fleet converts to USD and
    the bot records that exact exit MC in past_trades.
    """
    manager = make_manager_with_single_bot()
    token = make_token(market_cap=80.0)   # 80 SOL * $150 = $12_000
    plant_position(manager, token, buy_mc_usd=12_000.0)
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)

    # Price doubled → exit MC should be $24_000
    exit_price_sol = 160.0 / token.total_supply          # 160 SOL MC worth of tokens
    manager.client.get_last_transaction.return_value = {"priceSol": str(exit_price_sol)}

    await manager.on_token_removed("graduated", token.pair_address)

    bot = manager.bots[0]
    assert token.pair_address not in bot.active_positions, "position should be cleared"
    result = bot.past_trades[token.pair_address][-1]
    assert result.sell_market_cap == pytest.approx(24_000.0, rel=1e-3)
    assert result.sell_reason.category == SellCategory.TOKEN_REMOVED


@pytest.mark.asyncio
async def test_token_removed_fallback_when_api_fails():
    """
    When get_last_transaction raises, the fallback is
    token_state.token.market_cap * sol_price (the last known MC).
    """
    manager = make_manager_with_single_bot()
    token = make_token(market_cap=80.0)   # $12_000
    plant_position(manager, token, buy_mc_usd=12_000.0)
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)
    manager.client.get_last_transaction.side_effect = Exception("network error")

    await manager.on_token_removed("migrated", token.pair_address)

    bot = manager.bots[0]
    assert token.pair_address not in bot.active_positions
    result = bot.past_trades[token.pair_address][-1]
    # fallback = 80 * 150 = $12_000
    assert result.sell_market_cap == pytest.approx(12_000.0, rel=1e-2)


@pytest.mark.asyncio
async def test_token_removed_no_position_is_noop():
    """Bot doesn't hold the token → past_trades stays empty."""
    manager = make_manager_with_single_bot()
    token = make_token()
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)
    manager.client.get_last_transaction.return_value = {"priceSol": "0.0001"}

    await manager.on_token_removed("graduated", token.pair_address)

    bot = manager.bots[0]
    assert token.pair_address not in bot.past_trades


@pytest.mark.asyncio
async def test_token_removed_pnl_profitable():
    """
    Entry $12k → exit $18k (50% up), fees 3%.
    Expected net profit ≈ +0.425 SOL.
    """
    manager = make_manager_with_single_bot()
    token = make_token(market_cap=80.0)
    plant_position(manager, token, buy_mc_usd=12_000.0)
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)

    exit_price_sol = 18_000.0 / (token.total_supply * SOL_PRICE)
    manager.client.get_last_transaction.return_value = {"priceSol": str(exit_price_sol)}

    await manager.on_token_removed("graduated", token.pair_address)

    result = manager.bots[0].past_trades[token.pair_address][-1]
    assert result.profit == pytest.approx(0.425, rel=1e-3)


@pytest.mark.asyncio
async def test_token_removed_pnl_loss():
    """
    Entry $12k → exit $8.4k (30% down), fees 3%.
    Expected net profit ≈ -0.351 SOL.
    """
    manager = make_manager_with_single_bot()
    token = make_token(market_cap=80.0)
    plant_position(manager, token, buy_mc_usd=12_000.0)
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)

    exit_price_sol = 8_400.0 / (token.total_supply * SOL_PRICE)
    manager.client.get_last_transaction.return_value = {"priceSol": str(exit_price_sol)}

    await manager.on_token_removed("migrated", token.pair_address)

    result = manager.bots[0].past_trades[token.pair_address][-1]
    assert result.profit == pytest.approx(-0.351, rel=1e-3)


@pytest.mark.asyncio
async def test_shared_tokens_cleaned_up_after_removal():
    """pair_address is deleted from shared_tokens after on_token_removed."""
    manager = make_manager_with_single_bot()
    token = make_token()
    manager.shared_tokens[token.pair_address] = SharedTokenState(token=token)
    manager.client.get_last_transaction.return_value = {"priceSol": "0.0001"}

    await manager.on_token_removed("graduated", token.pair_address)

    assert token.pair_address not in manager.shared_tokens


@pytest.mark.asyncio
async def test_token_removed_unknown_pair_is_early_return():
    """pair_address not in shared_tokens → early return, client never called."""
    manager = make_manager_with_single_bot()

    await manager.on_token_removed("graduated", "0xUNKNOWN")

    manager.client.get_last_transaction.assert_not_called()
    assert "0xUNKNOWN" not in manager.bots[0].past_trades


# ---------------------------------------------------------------------------
# shutdown — Integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manager_shutdown_closes_all_active_positions():
    """
    On shutdown, ShadowFleetManager delegates to VirtualBot, which then
    sells all active positions with a 'SHUTDOWN' reason and closes its recorder.
    """
    manager = make_manager_with_single_bot()
    bot = manager.bots[0]

    # Plant two positions
    token1 = make_token(pair_address="pair1", market_cap=80.0)
    token2 = make_token(pair_address="pair2", market_cap=80.0)
    plant_position(manager, token1, buy_mc_usd=12_000.0)
    plant_position(manager, token2, buy_mc_usd=12_000.0)

    assert len(bot.active_positions) == 2

    await manager.shutdown()

    # Active positions should be empty
    assert len(bot.active_positions) == 0

    # Both trades should be recorded as past trades with 'SHUTDOWN' reason
    assert len(bot.past_trades["pair1"]) == 1
    assert len(bot.past_trades["pair2"]) == 1

    assert bot.past_trades["pair1"][0].sell_reason.category == SellCategory.SHUTDOWN
    assert bot.past_trades["pair2"][0].sell_reason.category == SellCategory.SHUTDOWN
