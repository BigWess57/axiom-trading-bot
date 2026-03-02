"""
Tests for should_sell() and its internal helpers _check_for_sl_tp().

Each test covers one exit reason in isolation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.pulse.types import SellCategory
from __tests__.conftest import make_token, make_trade_info, make_strategy, make_state


SOL = 150.0
BUY_MC = 12000.0  # Reference buy market cap in USD


@pytest.fixture
def strategy():
    return make_strategy(
        sol_price=SOL,
        stop_loss_pct=0.30,      # Sell if MC drops 30%
        take_profit_pct=0.60,    # Sell if MC rises 60%
        max_holding_time=300,    # 5 minutes
    )


# ── Gate: SOL price ───────────────────────────────────────────────────────────

def test_no_sell_without_sol_price():
    strategy = make_strategy(sol_price=0.0)
    trade = make_trade_info()
    assert strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot)) is None


# ── Gate: category change ─────────────────────────────────────────────────────

def test_sell_category_change(strategy):
    token = make_token(category="migrated")
    trade = make_trade_info(token=token)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.CATEGORY_CHANGE


def test_no_sell_still_in_final_stretch(strategy):
    token = make_token(category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    # MC hasn't moved, time is fine → no sell
    assert strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot)) is None


# ── Gate: security ────────────────────────────────────────────────────────────

def test_sell_security_failed(strategy):
    token = make_token(top10_holders_percent=99.0)  # Fail security
    trade = make_trade_info(token=token)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.SECURITY_FAILED


# ── Gate: stop loss ───────────────────────────────────────────────────────────

def test_sell_stop_loss_triggered(strategy):
    # Buy MC = $12_000; SL at 30% → sell below $8_400
    # Set current MC to $7_000: market_cap = 7000 / 150 ≈ 46.67 SOL
    token = make_token(market_cap=46.67, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.STOP_LOSS


def test_no_sell_just_above_stop_loss(strategy):
    # Buy MC = $12_000; 30% SL threshold = $8_400
    # Current MC = $8_500 → above threshold
    token = make_token(market_cap=8500 / SOL, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    assert strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot)) is None


# ── Gate: take profit ─────────────────────────────────────────────────────────

def test_sell_take_profit_triggered(strategy):
    # Buy MC = $12_000; TP at 60% → sell above $19_200
    # Set current MC to $20_000
    token = make_token(market_cap=20000 / SOL, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.TAKE_PROFIT


def test_no_sell_just_below_take_profit(strategy):
    # TP threshold = $19_200; current MC = $19_000 → below threshold
    token = make_token(market_cap=19000 / SOL, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    assert strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot)) is None


# ── Gate: max hold time ───────────────────────────────────────────────────────

def test_sell_max_hold_time_exceeded(strategy):
    token = make_token(category="finalStretch")
    # Held for 310 seconds, max = 300
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=310)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.MAX_HOLD_TIME


def test_no_sell_within_hold_time(strategy):
    token = make_token(category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=100)
    assert strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot)) is None


# ── SL/TP detail strings ──────────────────────────────────────────────────────

def test_stop_loss_details_contain_percentage(strategy):
    token = make_token(market_cap=46.67, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert "%" in reason.details


def test_take_profit_details_contain_percentage(strategy):
    token = make_token(market_cap=20000 / SOL, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=BUY_MC, seconds_held=10)
    reason = strategy.should_sell(trade, make_state(token=trade.token_bought_snapshot))
    assert "%" in reason.details
