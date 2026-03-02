"""
Tests for should_buy().

Each test isolates a single gate in the buy-signal decision chain.
The fixture provides a token + state that passes ALL gates; tests
then break exactly one condition to verify the correct rejection.
"""
import pytest
from datetime import datetime, timezone, timedelta
from __tests__.conftest import (
    make_token, make_state, make_strategy, make_past_trade, make_snapshot, _seconds_ago_iso
)


SOL = 150.0
# At SOL=150, make_token() market_cap=80 → MC = $12_000 (within [9k, 18k])


@pytest.fixture
def strategy():
    # Tweak baseline so default state (hs=0.8) reaches min_confidence=50
    # baseline(30) + high_holder_safety(10) + buying_pressure needs activity
    # To avoid activity dependency in buy tests, raise baseline high enough
    return make_strategy(sol_price=SOL, baseline_confidence_score=50.0)


def passing_state(**token_overrides) -> tuple:
    """Return a (state, strategy) pair that should always produce should_buy=True."""
    token = make_token(**token_overrides)
    state = make_state(token=token, holder_safety_score=0.8)
    # Add enough snapshots for full activity evaluation
    now = datetime.now(timezone.utc)
    # Old snapshot (>60s ago): 10 txns, 5 buys, 5 sells
    state.snapshots = [
        make_snapshot(seconds_ago=90, txns=10, buys=5, sells=5),
        make_snapshot(seconds_ago=70, txns=50, buys=30, sells=20),
        # Recent snapshots
        make_snapshot(seconds_ago=30, txns=120, buys=80, sells=40),
        make_snapshot(seconds_ago=10, txns=160, buys=100, sells=60),
    ]
    return state


# ── Gate: SOL price ───────────────────────────────────────────────────────────

def test_no_buy_without_sol_price():
    strategy = make_strategy(sol_price=0.0, baseline_confidence_score=50.0)
    state = passing_state()
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


# ── Gate: category ────────────────────────────────────────────────────────────

def test_no_buy_wrong_category(strategy):
    state = passing_state(category="newPairs")
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


def test_no_buy_no_category(strategy):
    state = passing_state(category=None)
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


# ── Gate: security ────────────────────────────────────────────────────────────

def test_no_buy_security_fails_top10(strategy):
    state = passing_state(top10_holders_percent=99.0)
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


# ── Gate: confidence ─────────────────────────────────────────────────────────

def test_no_buy_low_confidence():
    # baseline=30, no boosts (bad safety, ATH penalty) → below min_confidence=50
    strategy = make_strategy(sol_price=SOL, baseline_confidence_score=30.0)
    token = make_token()
    # Holder safety score below 0.33 → penalty -30 → score = max(0, 30-30) = 0
    state = make_state(token=token, holder_safety_score=0.1, ath_market_cap=12000.0)
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


# ── Gate: trade limits ────────────────────────────────────────────────────────

def test_no_buy_max_trades_reached(strategy):
    token = make_token()
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=600) for _ in range(3)]
    state = passing_state()
    state.token = token
    state.past_trades = past
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


def test_no_buy_still_in_cooldown(strategy):
    token = make_token()
    # Sold only 60 seconds ago, cooldown = 3 minutes
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=60)]
    state = passing_state()
    state.token = token
    state.past_trades = past
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


def test_buy_allowed_after_cooldown(strategy):
    token = make_token()
    # Sold 200 seconds ago, cooldown = 3 min (180s) → should be fine
    past = [make_past_trade(pair_address=token.pair_address, seconds_ago_sold=200)]
    state = passing_state()
    state.token = token
    state.past_trades = past
    ok, _, _ = strategy.should_buy(state)
    assert ok is True


# ── Gate: token age ───────────────────────────────────────────────────────────

def test_no_buy_token_too_old(strategy):
    # created 700 seconds ago, max = 600
    state = passing_state(created_at=_seconds_ago_iso(700))
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


def test_buy_allowed_fresh_token(strategy):
    state = passing_state(created_at=_seconds_ago_iso(30))
    ok, _, _ = strategy.should_buy(state)
    assert ok is True


# ── Gate: market cap range ────────────────────────────────────────────────────

def test_no_buy_mc_too_low(strategy):
    # market_cap=50 * sol=150 = $7_500 < min $9_000
    state = passing_state(market_cap=50.0, volume_total=60.0)
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


def test_no_buy_mc_too_high(strategy):
    # market_cap=150 * sol=150 = $22_500 > max $18_000
    state = passing_state(market_cap=150.0, volume_total=200.0)
    ok, _, _ = strategy.should_buy(state)
    assert ok is False


# ── Gate: volume ──────────────────────────────────────────────────────────────

# def test_no_buy_volume_below_market_cap(strategy):
#     # volume=50 < market_cap=80
#     state = passing_state(volume_total=50.0, market_cap=80.0)
#     ok, _, _ = strategy.should_buy(state)
#     assert ok is False


# ── Position sizing ───────────────────────────────────────────────────────────

def test_buy_returns_min_size_at_baseline():
    """
    When confidence == min_confidence_score, size = min_position_size.
    We'll set baseline=50, min=50. Result confidence = 50.
    """
    strategy = make_strategy(
        sol_price=SOL,
        baseline_confidence_score=50.0,
        min_confidence_score=50.0,
        good_confidence_score=100.0,
    )
    # No boosts: holder_safety_score=0.5 (neutral), no snapshots => confidence = 50
    state = passing_state()
    state.snapshots = []
    state.holder_safety_score = 0.5
    state.ath_market_cap = 12000.0
    ok, size, _ = strategy.should_buy(state)
    assert ok is True
    # By default, min_position_size=0.3
    assert size == pytest.approx(strategy.config.risk.min_position_size)


def test_buy_returns_interpolated_size():
    """
    When confidence is between min and 100, size is linearly interpolated.
    We set baseline=50, min=50. We add logic to get confidence = 75.
    (75-50)/(100-50) = 0.5 ratio
    size = min_size + 0.5 * (max_size - min_size)
    """
    strategy = make_strategy(
        sol_price=SOL,
        baseline_confidence_score=50.0,
        min_confidence_score=50.0,
        good_confidence_score=100.0,
        confidence_boost_high_holder_safety=25.0, # Will give +25 to get exactly 75
        holder_safety_threshold_high=0.8,
    )
    state = passing_state()
    state.snapshots = []
    # Trigger max holder safety boost (score >= 0.8)
    state.holder_safety_score = 0.9
    state.ath_market_cap = 12000.0
    
    ok, size, conf = strategy.should_buy(state)
    assert ok is True
    
    # Calculate exactly what size should be based on the dynamic config
    min_conf = strategy.config.confidence.min_confidence_score
    max_conf = strategy.config.confidence.good_confidence_score
    
    # Verify we are actually in the middle range for a meaningful test
    assert min_conf < conf < max_conf
    
    expected_ratio = (conf - min_conf) / (max_conf - min_conf)
    expected_size = strategy.config.risk.min_position_size + expected_ratio * (strategy.config.risk.max_position_size - strategy.config.risk.min_position_size)
    assert size == pytest.approx(expected_size)
