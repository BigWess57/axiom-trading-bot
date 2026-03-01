"""
Tests for _calculate_confidence().

Each test activates exactly one confidence factor and verifies its
contribution to the overall score (in addition to the baseline).
"""
import pytest
from datetime import datetime, timezone, timedelta
from __tests__.conftest import make_token, make_state, make_strategy, make_snapshot


SOL = 150.0
BASELINE = 30.0


@pytest.fixture
def strategy():
    return make_strategy(
        sol_price=SOL,
        baseline_confidence_score=BASELINE,
        # Explicit weights to make math deterministic
        confidence_boost_high_holder_safety=10.0,
        confidence_penalty_low_holder_safety=30.0,
        holder_safety_threshold_high=0.66,
        holder_safety_threshold_low=0.33,
        ath_impact_threshold=0.4,
        confidence_penalty_ath_impact=20.0,
        distribution_trend_lookback=5,
        confidence_boost_improving_distribution_ratio=10.0,
        confidence_penalty_worsening_distribution_ratio=10.0,
        activity_lookback_seconds=60,
        min_txns_for_boost=50,
        confidence_boost_high_activity=10.0,
        confidence_boost_buying_pressure=5.0,
    )


def _bare_state(**overrides):
    """State with NO optional factors active (no snapshots, neutral safety)."""
    token = make_token()
    state = make_state(
        token=token,
        holder_safety_score=None,  # No safety score → no boost/penalty
        ath_market_cap=0.0,        # 0 ATH → ATH penalty won't fire
        snapshots=[],
    )
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


# ── Baseline ──────────────────────────────────────────────────────────────────

def test_baseline_with_no_factors(strategy):
    state = _bare_state()
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE)


def test_zero_sol_price_returns_zero(strategy):
    state = _bare_state()
    assert strategy._calculate_confidence(state, 0.0) == pytest.approx(0.0)


# ── Holder safety ─────────────────────────────────────────────────────────────

def test_high_holder_safety_gives_boost(strategy):
    state = _bare_state(holder_safety_score=0.9)  # > 0.66
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE + 10.0)


def test_mid_holder_safety_no_change(strategy):
    state = _bare_state(holder_safety_score=0.5)  # between 0.33 and 0.66
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE)


def test_low_holder_safety_gives_penalty(strategy):
    state = _bare_state(holder_safety_score=0.1)  # < 0.33
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(max(0.0, BASELINE - 30.0))


# ── ATH impact ────────────────────────────────────────────────────────────────

def test_ath_penalty_when_mc_far_below_ath(strategy):
    """
    Current MC = $12_000; ATH = $31_000
    $12_000 / $31_000 ≈ 0.387 < ath_impact_threshold=0.4 → penalty -20
    """
    state = _bare_state(ath_market_cap=31_000.0)  # token.market_cap=80 * 150 = 12_000
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE - 20.0)


def test_no_ath_penalty_when_mc_near_ath(strategy):
    """Current MC = $12_000; ATH = $13_000 → 12k/13k ≈ 0.92 > 0.4 → no penalty."""
    state = _bare_state(ath_market_cap=13_000.0)
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE)


def test_no_ath_penalty_when_ath_is_zero(strategy):
    """ATH = 0 → condition can't fire (division by zero guard in code)."""
    state = _bare_state(ath_market_cap=0.0)
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE)


# ── Distribution trend (MC/holders ratio) ─────────────────────────────────────

def _make_distribution_snapshots(ratios: list) -> list:
    """Build snapshots with specific market_cap/holders ratios."""
    snapshots = []
    for i, ratio in enumerate(ratios):
        # holders=1000, market_cap = ratio * 1000
        snapshots.append(make_snapshot(
            seconds_ago=200 - i * 30,
            market_cap=ratio * 1000,
            holders=1000,
        ))
    return snapshots


def test_improving_distribution_gives_boost(strategy):
    """
    Ratio is decreasing (more holders relative to MC) → +10.
    Snapshots: past_ratios=[20,19,18,17,16] (USD/holder), avg_prev=18.5, latest=16.
    Token current_ratio = 14 < avg_prev → boost.
    market_cap (SOL) = target_USD_ratio * holders / SOL = 14 * 1000 / 150 ≈ 93.3
    """
    target_ratio = 14  # USD per holder, must be < avg_prev=18.5
    token = make_token(market_cap=target_ratio * 1000 / SOL, holders=1000)
    state = _bare_state()
    state.token = token
    state.snapshots = _make_distribution_snapshots([20, 19, 18, 17, 16])
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE + 10.0)


# def test_worsening_distribution_gives_penalty(strategy):
#     """
#     Ratio is increasing (fewer holders relative to MC) → -10.
#     Snapshots: past_ratios=[10,12,14,16,18] (USD/holder), avg_prev=13, latest=18.
#     Token current_ratio = 20 > avg_prev=13 → penalty.
#     market_cap (SOL) = 20 * 1000 / 150 ≈ 133.3
#     """
#     target_ratio = 20  # USD per holder, must be > avg_prev=13
#     token = make_token(market_cap=target_ratio * 1000 / SOL, holders=1000)
#     state = _bare_state()
#     state.token = token
#     state.snapshots = _make_distribution_snapshots([10, 12, 14, 16, 18])
#     score = strategy._calculate_confidence(state, SOL)
#     assert score == pytest.approx(BASELINE - 10.0)


# def test_still_changes_distribution_without_enough_snapshots(strategy):
#     """Fewer than lookback=5 snapshots → distribution factor still checked on these ones."""
#     target_ratio = 20  # USD per holder, must be > avg_prev=13
#     token = make_token(market_cap=target_ratio * 1000 / SOL, holders=1000)
#     state = _bare_state()
#     state.token = token
#     state.snapshots = _make_distribution_snapshots([10, 12, 14, 16]) #One less than lookback
#     score = strategy._calculate_confidence(state, SOL)
#     assert score == pytest.approx(BASELINE - 10)


# ── Activity (txns in last 60s) ───────────────────────────────────────────────

def _activity_state(old_txns: int, new_txns: int, old_buys: int, new_buys: int,
                    old_sells: int, new_sells: int) -> object:
    """Snapshots spanning the 60-second activity window."""
    state = _bare_state()
    # Snapshot just outside the 60s window → used as baseline
    old = make_snapshot(seconds_ago=90, txns=old_txns, buys=old_buys, sells=old_sells)
    # Recent snapshot (within window)
    recent = make_snapshot(seconds_ago=10, txns=new_txns, buys=new_buys, sells=new_sells)
    state.snapshots = [old, recent]
    return state


def test_high_activity_gives_boost(strategy):
    """new_txns = 160 - 10 = 150 > min_txns_for_boost=50 → +10."""
    state = _activity_state(
        old_txns=10, new_txns=160,
        old_buys=5, new_buys=100,
        old_sells=5, new_sells=60,
    )
    score = strategy._calculate_confidence(state, SOL)
    assert score >= BASELINE + 10.0  # At minimum the activity boost


def test_buying_pressure_gives_boost(strategy):
    """new_buys > new_sells → +5."""
    state = _activity_state(
        old_txns=10, new_txns=30,  # delta=20, below min_txns → no activity boost
        old_buys=5, new_buys=25,   # delta buys=20
        old_sells=5, new_sells=10, # delta sells=5 → buys > sells → +5
    )
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE + 5.0)


def test_no_activity_boost_low_txns(strategy):
    """new_txns = 40 → below min_txns_for_boost=50 → no boost."""
    state = _activity_state(
        old_txns=10, new_txns=50,  # delta=40 < 50
        old_buys=5, new_buys=5,    # equal buys/sells → no buying pressure
        old_sells=5, new_sells=5,
    )
    score = strategy._calculate_confidence(state, SOL)
    assert score == pytest.approx(BASELINE)


# ── Score clamping ────────────────────────────────────────────────────────────

def test_score_cannot_go_below_zero(strategy):
    """Combined penalties must not produce a negative score."""
    # low safety (-30), ATH penalty (-20) → 30 - 30 - 20 = -20 → clamped to 0
    state = _bare_state(holder_safety_score=0.1, ath_market_cap=100_000.0)
    score = strategy._calculate_confidence(state, SOL)
    assert score >= 0.0


def test_score_cannot_exceed_100(strategy):
    """Combined boosts must not produce a score above 100."""
    strategy_high = make_strategy(
        sol_price=SOL,
        baseline_confidence_score=90.0,
        confidence_boost_high_holder_safety=10.0,
        confidence_boost_high_activity=10.0,
        confidence_boost_buying_pressure=10.0,
        confidence_boost_improving_distribution_ratio=10.0,
        min_txns_for_boost=1,
    )
    state = _activity_state(
        old_txns=0, new_txns=100,
        old_buys=0, new_buys=80,
        old_sells=0, new_sells=10,
    )
    state.holder_safety_score = 0.9
    state.ath_market_cap = 0.0
    score = strategy_high._calculate_confidence(state, SOL)
    assert score <= 100.0
