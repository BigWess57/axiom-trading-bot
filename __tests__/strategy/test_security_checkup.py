"""
Tests for _security_checkup().

Each test mutates exactly one field on an otherwise-passing token
to the boundary that triggers a failure.
"""
import pytest
from __tests__.conftest import make_token, make_strategy


SOL = 150.0


@pytest.fixture
def strategy():
    return make_strategy(sol_price=SOL)


# ── Passing case ──────────────────────────────────────────────────────────────

def test_passes_clean_token(strategy):
    token = make_token()
    assert strategy._security_checkup(token, SOL) is None


# ── Individual failure cases ──────────────────────────────────────────────────

def test_fails_top10_holders(strategy):
    token = make_token(top10_holders_percent=51.0)  # max = 50
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "Top 10" in result


def test_fails_dev_holding(strategy):
    token = make_token(dev_holding_percent=21.0)  # max = 20
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "Dev" in result


def test_fails_insiders(strategy):
    token = make_token(insiders_percent=31.0)  # max = 30
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "Insiders" in result


def test_fails_bundled(strategy):
    token = make_token(bundled_percent=51.0)  # max = 50
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "Bundled" in result


def test_fails_no_holders(strategy):
    token = make_token(holders=0)
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "holders" in result.lower()


def test_fails_no_fees(strategy):
    token = make_token(fees_paid=0)
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "fees" in result.lower()


def test_fails_low_pro_traders(strategy):
    # 19 pro traders out of 100 holders = 19% < min 20%
    token = make_token(pro_traders_count=19, holders=100)
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "pro trader" in result.lower()


def test_fails_volume_fees_ratio(strategy):
    # volume_total=200, sol_price=150, fees_paid=1 → ratio = 30_000 > 20_000
    token = make_token(volume_total=200.0, fees_paid=1.0)
    result = strategy._security_checkup(token, SOL)
    assert result is not None
    assert "ratio" in result.lower()


# ── Boundary cases ────────────────────────────────────────────────────────────

def test_passes_at_exact_top10_limit(strategy):
    """Exactly at the limit should still pass (strict >)."""
    token = make_token(top10_holders_percent=50.0)
    assert strategy._security_checkup(token, SOL) is None


def test_passes_at_exact_pro_trader_limit(strategy):
    """Exactly at the pro-trader threshold should pass (strict <)."""
    # 20 / 100 = 20.0% == min_pro_trader_percent → should pass
    token = make_token(pro_traders_count=20, holders=100)
    assert strategy._security_checkup(token, SOL) is None
