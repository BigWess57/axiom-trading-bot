import pytest
from datetime import datetime, timezone, timedelta
from src.pulse.types import SellCategory
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG
from __tests__.conftest import make_token, make_trade_info, make_strategy, make_state, make_snapshot

SOL = 150.0

@pytest.fixture
def strategy():
    return make_strategy(sol_price=SOL)


def test_hold_confidence_perfect_metrics_starts_100(strategy):
    token = make_token()
    trade = make_trade_info(token=token, buy_market_cap=12000.0)
    state = make_state(token=token)
    state.active_trade = trade
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 100.0


def test_exodus_penalty(strategy):
    token = make_token(holders=700) # Current is 700
    trade = make_trade_info(token=token, seconds_held=120)
    state = make_state(token=token)
    state.active_trade = trade
    
    # Simulate that highest holder count was 1000 during trade
    snap1 = make_snapshot(seconds_ago=100, holders=900)
    snap2 = make_snapshot(seconds_ago=60, holders=1000)
    snap3 = make_snapshot(seconds_ago=30, holders=800)
    state.snapshots = [snap1, snap2, snap3]
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 75.0 # 100 - 25


def test_hype_death_penalty(strategy):
    token = make_token(active_users_watching=70)
    trade = make_trade_info(token=token, seconds_held=120)
    state = make_state(token=token)
    state.active_trade = trade
    
    snap1 = make_snapshot(seconds_ago=30, users_watching=90)
    snap2 = make_snapshot(seconds_ago=20, users_watching=100)
    snap3 = make_snapshot(seconds_ago=10, users_watching=80)
    state.snapshots = [snap1, snap2, snap3]
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 85.0 # 100 - 15


def test_sell_pressure_penalty(strategy):
    token = make_token(sells_total=150, buys_total=125)
    trade = make_trade_info(token=token, seconds_held=120)
    state = make_state(token=token)
    state.active_trade = trade
    
    snap_30s_ago = make_snapshot(seconds_ago=30, sells=100, buys=100, txns=200)
    state.snapshots = [snap_30s_ago]
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 75.0 # 100 - 25


def test_velocity_death_penalty(strategy):
    token = make_token(txns_total=350)
    trade = make_trade_info(token=token, seconds_held=120)
    state = make_state(token=token)
    state.active_trade = trade
    
    snap90 = make_snapshot(seconds_ago=90, txns=100)
    snap60 = make_snapshot(seconds_ago=60, txns=200)
    snap30 = make_snapshot(seconds_ago=30, txns=300)
    
    state.snapshots = [snap90, snap60, snap30]
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 70.0 # 100 - 30


def test_safety_breach_penalty(strategy):
    token = make_token(top10_holders_percent=45.0)
    trade = make_trade_info(token=token)
    state = make_state(token=token)
    state.active_trade = trade
    
    score = strategy._calculate_hold_confidence(state, SOL)
    assert score == 85.0 # 100 - 15


def test_low_confidence_triggers_sell_reason(strategy):
    token = make_token(txns_total=350, holders=700)
    trade = make_trade_info(token=token, seconds_held=120)
    state = make_state(token=token)
    state.active_trade = trade
    
    snap90 = make_snapshot(seconds_ago=90, txns=100, holders=900)
    snap60 = make_snapshot(seconds_ago=60, txns=200, holders=1000)
    snap30 = make_snapshot(seconds_ago=30, txns=300, holders=800)
    state.snapshots = [snap90, snap60, snap30]
    
    reason = strategy.should_sell(trade, state)
    assert reason is not None
    assert reason.category == SellCategory.LOW_CONFIDENCE
