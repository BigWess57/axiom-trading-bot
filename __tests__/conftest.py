"""
Shared fixtures for strategy unit tests.

Design philosophy:
- make_token() produces a PASSING token by default — tests that check failures
  should only mutate the single field they're testing.
- make_config() mirrors DEFAULT_STRATEGY_CONFIG so tests reflect real behaviour.
- Timestamps are in UTC ISO-8601 format to satisfy PulseToken.from_array parsing.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.pulse.types import (
    PulseToken,
    TokenState,
    TokenSnapshot,
    TradeTakenInformation,
    TradeResult,
    SellReason,
    SellCategory,
)
from src.pulse.trading.strategies.strategy_config import StrategyConfig
from src.pulse.trading.strategies.core_strategy import CoreStrategy


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # Account
    "starting_balance": 20,
    "fees_percentage": 0.03,
    # Risk
    "max_position_size": 1.0,
    "max_daily_trades": 20,
    "stop_loss_pct": 0.30,
    "take_profit_pct": 0.60,
    "max_holding_time": 300,
    "max_trades_per_token": 3,
    "cooldown_minutes": 3,
    # Safety
    "min_holder_sol_balance": 1.0,
    "holder_check_count": 30,
    "max_top10_percent": 50.0,
    "max_dev_holding_percent": 20.0,
    "max_insiders_percent": 30.0,
    "max_bundled_percent": 50.0,
    "min_pro_trader_percent": 20.0,
    "max_volume_fees_ratio": 20000.0,
    # Buy rules
    "max_token_age_seconds": 600,
    "min_market_cap": 9000.0,
    "max_market_cap": 18000.0,
    # Confidence
    "baseline_confidence_score": 30.0,
    "min_confidence_score": 50.0,
    "good_confidence_score": 70.0,
    "confidence_boost_high_holder_safety": 10.0,
    "confidence_penalty_low_holder_safety": 30.0,
    "confidence_boost_improving_distribution_ratio": 10.0,
    "confidence_penalty_worsening_distribution_ratio": 10.0,
    "holder_safety_threshold_high": 0.66,
    "holder_safety_threshold_low": 0.33,
    "ath_impact_threshold": 0.4,
    "confidence_penalty_ath_impact": 20.0,
    "distribution_trend_lookback": 5,
    "activity_lookback_seconds": 60,
    "min_txns_for_boost": 50,
    "confidence_boost_high_activity": 10.0,
    "confidence_boost_buying_pressure": 5.0,
}


def make_config(**overrides) -> StrategyConfig:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(overrides)
    return StrategyConfig(cfg)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _seconds_ago_iso(seconds: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return dt.isoformat().replace("+00:00", "Z")


def make_token(**overrides) -> PulseToken:
    """A token that PASSES all security and buy-signal checks by default at SOL=$150."""
    # At sol_price=150: market_cap=80 SOL → $12_000 (within [9k, 18k])
    # volume_total=100 > market_cap=80 ✓
    defaults = dict(
        pair_address="pair_abc",
        token_address="tok_abc",
        creator="creator_abc",
        name="TestCoin",
        ticker="TST",
        image=None,
        chain_id=101,
        protocol="raydium",
        category="finalStretch",
        # Holder safety — all pass
        top10_holders_percent=40.0,   # < 50
        dev_holding_percent=10.0,     # < 20
        insiders_percent=20.0,        # < 30
        bundled_percent=30.0,         # < 50
        holders=500,
        # Financial
        volume_total=100.0,           # > market_cap=80
        market_cap=80.0,              # * 150 = $12_000
        fees_paid=5.0,                # > 0
        total_supply=1_000_000.0,
        # Activity
        txns_total=200,
        buys_total=120,
        sells_total=80,
        pro_traders_count=200,        # 200/500 = 40% > 20%
        # Timestamps: created 60s ago (well within 600s window)
        created_at=_seconds_ago_iso(60),
        migrated_at=_seconds_ago_iso(120),
    )
    defaults.update(overrides)
    return PulseToken(**defaults)


# ---------------------------------------------------------------------------
# TokenState / TokenSnapshot
# ---------------------------------------------------------------------------

def make_snapshot(seconds_ago: int = 0, **overrides) -> TokenSnapshot:
    defaults = dict(
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=seconds_ago),
        market_cap=12000.0,
        txns=100,
        buys=60,
        sells=40,
        holders=500,
    )
    defaults.update(overrides)
    return TokenSnapshot(**defaults)


def make_state(token: Optional[PulseToken] = None, **overrides) -> TokenState:
    if token is None:
        token = make_token()
    defaults = dict(
        token=token,
        past_trades=[],
        ath_market_cap=12000.0,
        snapshots=[],
        holder_safety_score=0.8,   # High safety by default → confidence boost
    )
    defaults.update(overrides)
    return TokenState(**defaults)


# ---------------------------------------------------------------------------
# Trade helpers
# ---------------------------------------------------------------------------

def make_trade_info(
    token: Optional[PulseToken] = None,
    buy_market_cap: float = 12000.0,
    seconds_held: int = 0,
    sol_price: float = 150.0,
    **overrides,
) -> TradeTakenInformation:
    if token is None:
        token = make_token()
    time_bought = datetime.now(timezone.utc) - timedelta(seconds=seconds_held)
    defaults = dict(
        token_bought_snapshot=token,
        buy_market_cap=buy_market_cap,
        current_market_cap=token.market_cap * sol_price,  # reflects live price at call time
        time_bought=time_bought,
        position_size=1.0,
        confidence=50.0,
    )
    defaults.update(overrides)
    return TradeTakenInformation(**defaults)


def make_past_trade(
    pair_address: str = "pair_abc",
    seconds_ago_sold: int = 300,
    **overrides,
) -> TradeResult:
    now = datetime.now(timezone.utc)
    defaults = dict(
        pair_address=pair_address,
        token_ticker="TST",
        token_name="TestCoin",
        profit=0.0,
        fees_paid=0.0,
        sell_reason=SellReason(category=SellCategory.TAKE_PROFIT),
        time_bought=now - timedelta(seconds=seconds_ago_sold + 60),
        time_sold=now - timedelta(seconds=seconds_ago_sold),
    )
    defaults.update(overrides)
    return TradeResult(**defaults)


# ---------------------------------------------------------------------------
# Strategy factory
# ---------------------------------------------------------------------------

def make_strategy(sol_price: float = 150.0, **config_overrides) -> CoreStrategy:
    config = make_config(**config_overrides)
    return CoreStrategy(config, lambda: sol_price)
