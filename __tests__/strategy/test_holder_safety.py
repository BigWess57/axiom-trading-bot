"""
Tests for check_holder_safety().

Verifies that holder_safety_score is correctly set on the state
based on holder SOL balances vs. the configured threshold.
"""
import pytest
from __tests__.conftest import make_token, make_state, make_strategy, make_config
from src.pulse.types import TokenState


SOL = 150.0

# Helper: build a raw holder list.
# Each entry is [address, pct, sol_balance, ...]
def _make_holders(count: int, balance: float) -> list:
    """All holders have the same SOL balance."""
    return [["addr_lp", 5.0, 999.0]] + [  # index 0 = LP, always skipped
        [f"addr_{i}", 1.0, balance] for i in range(count)
    ]


def _make_mixed_holders(rich: int, broke: int) -> list:
    """rich holders with 5 SOL, broke holders with 0.1 SOL."""
    lp = [["addr_lp", 5.0, 999.0]]
    rich_holders = [[f"rich_{i}", 1.0, 5.0] for i in range(rich)]
    broke_holders = [[f"broke_{i}", 1.0, 0.1] for i in range(broke)]
    return lp + rich_holders + broke_holders


@pytest.fixture
def strategy():
    return make_strategy(sol_price=SOL)


# ── Core cases ────────────────────────────────────────────────────────────────

def test_empty_holders_gives_low_score(strategy):
    """No holders after LP → score defaults to 0.2."""
    state = make_state()
    state.holder_safety_score = None
    holders = [["addr_lp", 5.0, 999.0]]  # only LP
    strategy.check_holder_safety(state, holders)
    assert state.holder_safety_score == pytest.approx(0.2)


def test_all_rich_holders_score_is_one(strategy):
    """All holders have plenty of SOL → score = 1.0."""
    state = make_state()
    holders = _make_holders(count=10, balance=10.0)  # all above min=1.0
    strategy.check_holder_safety(state, holders)
    assert state.holder_safety_score == pytest.approx(1.0)


def test_all_broke_holders_score_is_zero(strategy):
    """All holders below threshold → score = 0.0."""
    state = make_state()
    holders = _make_holders(count=10, balance=0.5)  # all below min=1.0
    strategy.check_holder_safety(state, holders)
    assert state.holder_safety_score == pytest.approx(0.0)


def test_mixed_holders_correct_ratio(strategy):
    """20 rich + 10 broke out of 30 → score ≈ 0.667."""
    state = make_state()
    holders = _make_mixed_holders(rich=20, broke=10)
    strategy.check_holder_safety(state, holders)
    assert state.holder_safety_score == pytest.approx(20 / 30, rel=1e-3)


def test_score_only_checks_configured_count(strategy):
    """
    holder_check_count=30 means only indices [1..31] are examined.
    Extra holders beyond that window shouldn't affect the score.
    """
    # 30 rich holders + 100 broke ones outside the window
    rich = [[f"rich_{i}", 1.0, 10.0] for i in range(30)]
    broke_outside = [[f"broke_{i}", 1.0, 0.1] for i in range(100)]
    holders = [["lp", 5.0, 999.0]] + rich + broke_outside
    state = make_state()
    strategy.check_holder_safety(state, holders)
    # Only the first 30 non-LP holders were checked → all rich → score = 1.0
    assert state.holder_safety_score == pytest.approx(1.0)
