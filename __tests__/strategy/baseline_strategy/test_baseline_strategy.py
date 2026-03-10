import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from src.pulse.types import PulseToken, TokenState, SharedTokenState, TradeTakenInformation, TradeResult, SellCategory, SellReason
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig
from src.pulse.trading.strategies.baseline_strategy.baseline_strategy_main import BaselineStrategy
from src.config.baseline_strategy_config import get_baseline_config
from __tests__.conftest import make_state_from_shared_state

@pytest.fixture
def baseline_config():
    return BaselineStrategyConfig(get_baseline_config())

@pytest.fixture
def baseline_strategy(baseline_config):
    return BaselineStrategy(config=baseline_config, get_sol_price=lambda: 200.0)

SOL_PRICE = 200.0

def create_mock_token(mc_usd=10000, age_seconds=300, **kwargs):
    now = datetime.now(timezone.utc)
    created_at = datetime.fromtimestamp(now.timestamp() - age_seconds, timezone.utc)
    
    defaults = dict(
        pair_address="mock_pair",
        token_address="mock_base",
        creator="mock_creator",
        name="Mock Token",
        ticker="MOCK",
        image=None,
        chain_id=1,
        protocol="pump",
        market_cap=mc_usd / SOL_PRICE, # sol price = 200
        total_supply=1_000_000_000,
        volume_total=200.0,
        buys_total=100,
        sells_total=50,
        txns_total=150,
        holders=400,
        famous_kols=0,
        pro_traders_count=100,
        active_users_watching=10,
        dev_holding_percent=10,
        insiders_percent=10,
        bundled_percent=10,
        top10_holders_percent=40,
        fees_paid=5.0,
        created_at=created_at.isoformat().replace('+00:00', 'Z')
    )
    defaults.update(kwargs)
    return PulseToken(**defaults)

class MockSnapshot:
    def __init__(self, txns, buys, sells, users_watching, ts):
        self.txns = txns
        self.buys = buys
        self.sells = sells
        self.users_watching = users_watching
        self.timestamp = ts

# ==========================================
# BaselineSecurityMixin Tests
# ==========================================

def test_security_check_holder_safety(baseline_strategy):
    token = create_mock_token()
    shared_state = SharedTokenState(token=token)
    state = make_state_from_shared_state(shared_state)
    
    # 1 LP + 2 safe + 1 unsafe holder = 3 total checked
    holders = [
        ["LP", "ignore"],
        ["Holder1", "address", "2.0"], # safe
        ["Holder2", "address", "0.5"], # unsafe
        ["Holder3", "address", "5.0"]  # safe
    ]
    
    baseline_strategy.check_holder_safety(state, holders)
    
    # Total checked = 3. 2 are >= 1.0. Score = 2/3 = 0.666...
    assert abs(state.holder_safety_score - 0.666) < 0.01

def test_security_checkup_passes(baseline_strategy):
    token = create_mock_token()
    # All defaults should pass the strict baseline config
    reason = baseline_strategy._security_checkup(token, SOL_PRICE, holder_safety_score=0.9)
    assert reason is None

def test_security_checkup_fails_top10(baseline_strategy):
    # max top 10 is 50%
    token = create_mock_token(top10_holders_percent=55.0)
    reason = baseline_strategy._security_checkup(token, SOL_PRICE, holder_safety_score=0.9)
    assert "Top 10 holders own" in reason

def test_security_checkup_fails_holder_safety(baseline_strategy):
    # threshold is 0.4
    token = create_mock_token()
    reason = baseline_strategy._security_checkup(token, SOL_PRICE, holder_safety_score=0.2)
    assert "Holder safety score is too low" in reason


# ==========================================
# BaselineBuyRulesMixin Tests
# ==========================================

def test_buy_rules_pass_checkup(baseline_strategy):
    token = create_mock_token(mc_usd=10000, age_seconds=300)
    passes = baseline_strategy._pass_buy_rules_checkup(token, [], SOL_PRICE)
    assert passes is True

def test_buy_rules_fail_market_cap_too_high(baseline_strategy):
    token = create_mock_token(mc_usd=25000) # max is 18000
    passes = baseline_strategy._pass_buy_rules_checkup(token, [], SOL_PRICE)
    assert passes is False

def test_buy_rules_fail_market_cap_too_low(baseline_strategy):
    token = create_mock_token(mc_usd=3000) # min is 6000
    passes = baseline_strategy._pass_buy_rules_checkup(token, [], SOL_PRICE)
    assert passes is False

def test_buy_rules_fail_cooldown(baseline_strategy):
    token = create_mock_token()
    now = datetime.now(timezone.utc)
    
    # Trade sold 1 min ago (cooldown is 3 mins)
    recent_trade = TradeResult(
        pair_address="mock_pair", 
        token_ticker="TICK", 
        token_name="Name", 
        profit=1.0, 
        fees_paid=0.1, 
        sell_reason=SellReason(category=SellCategory.TAKE_PROFIT), 
        time_bought=now - timedelta(minutes=5), 
        time_sold=now - timedelta(minutes=1)
    )
    passes = baseline_strategy._pass_buy_rules_checkup(token, [recent_trade], SOL_PRICE)
    assert passes is False

def test_calculate_momentum_passes(baseline_strategy):
    token = create_mock_token()
    shared_state = SharedTokenState(token=token)
    
    now = datetime.now(timezone.utc)
    # lookback is 60 seconds
    past_timestamp = now - timedelta(seconds=65)
    
    past_snapshot = MockSnapshot(txns=100, buys=50, sells=50, users_watching=10, ts=past_timestamp)
    current_snapshot = MockSnapshot(txns=200, buys=150, sells=50, users_watching=110, ts=now)
    # delta: txns=100 (>50), buy/sell=100/0=Infinity (>1.5), watching=+100 (>50)
    
    shared_state.snapshots = [past_snapshot, current_snapshot]
    state = make_state_from_shared_state(shared_state)
    
    passes, reason = baseline_strategy._calculate_momentum(state)
    assert passes is True

def test_calculate_momentum_fails_low_txns(baseline_strategy):
    token = create_mock_token()
    shared_state = SharedTokenState(token=token)
    
    now = datetime.now(timezone.utc)
    past_timestamp = now - timedelta(seconds=65)
    
    past_snapshot = MockSnapshot(txns=100, buys=50, sells=50, users_watching=10, ts=past_timestamp)
    # txns delta = 40 (< 50)
    current_snapshot = MockSnapshot(txns=140, buys=130, sells=50, users_watching=110, ts=now) 
    
    shared_state.snapshots = [past_snapshot, current_snapshot]
    state = make_state_from_shared_state(shared_state)
    
    passes, reason = baseline_strategy._calculate_momentum(state)
    assert passes is False
    assert "Not enough txns" in reason

def test_calculate_momentum_fails_low_users_watching(baseline_strategy):
    token = create_mock_token()
    shared_state = SharedTokenState(token=token)
    
    now = datetime.now(timezone.utc)
    past_timestamp = now - timedelta(seconds=65)
    
    past_snapshot = MockSnapshot(txns=100, buys=50, sells=50, users_watching=10, ts=past_timestamp)
    # watching delta = 20 (< 50)
    current_snapshot = MockSnapshot(txns=200, buys=150, sells=50, users_watching=30, ts=now) 
    
    shared_state.snapshots = [past_snapshot, current_snapshot]
    state = make_state_from_shared_state(shared_state)
    
    passes, reason = baseline_strategy._calculate_momentum(state)
    assert passes is False
    assert "Not enough users watching" in reason

def test_calculate_momentum_users_watching_moving_average(baseline_strategy):
    # Test that the +/- 10s window is respected for the moving averages
    token = create_mock_token(active_users_watching=150) # The "current" raw token value
    shared_state = SharedTokenState(token=token)
    
    now = datetime.now(timezone.utc)
    past_timestamp = now - timedelta(seconds=60)
    
    # Old snapshot window: ts-11 (out), ts-5 (in), ts (in), ts+5 (in), ts+11 (out)
    snap_old_out1 = MockSnapshot(txns=100, buys=50, sells=50, users_watching=500, ts=past_timestamp - timedelta(seconds=11))
    snap_old_in1 = MockSnapshot(txns=100, buys=50, sells=50, users_watching=100, ts=past_timestamp - timedelta(seconds=5))
    snap_old_main = MockSnapshot(txns=100, buys=50, sells=50, users_watching=110, ts=past_timestamp)
    snap_old_in2 = MockSnapshot(txns=100, buys=50, sells=50, users_watching=80, ts=past_timestamp + timedelta(seconds=5))
    snap_old_out2 = MockSnapshot(txns=100, buys=50, sells=50, users_watching=500, ts=past_timestamp + timedelta(seconds=11))
    
    # New snapshot window: now-11 (out), now-5 (in), now (in)
    snap_new_out1 = MockSnapshot(txns=200, buys=150, sells=50, users_watching=10, ts=now - timedelta(seconds=11))
    snap_new_in1 = MockSnapshot(txns=200, buys=150, sells=50, users_watching=140, ts=now - timedelta(seconds=5))
    snap_new_main = MockSnapshot(txns=200, buys=150, sells=50, users_watching=160, ts=now)
    
    shared_state.snapshots = [
        snap_old_out1, snap_old_in1, snap_old_main, snap_old_in2, snap_old_out2,
        snap_new_out1, snap_new_in1, snap_new_main
    ]
    state = make_state_from_shared_state(shared_state)
    
    # Expected behavior:
    # old_users_ma = avg(100, 110, 80) = 96.67 (ignores the 500s because they are > 10s away)
    # current_users_vals = recent_snaps(140, 160) + token_val(150) = avg(140, 160, 150) = 150 (ignores the 10 because it's > 10s away)
    # delta = 150 - 96.67 = 53.33, so should pass
    
    passes, reason = baseline_strategy._calculate_momentum(state)
    assert passes is True
    assert "Momentum requirements met" in reason


# ==========================================
# BaselineRiskMixin Tests
# ==========================================

def test_risk_check_sl_tp_hits_take_profit(baseline_strategy):
    token = create_mock_token()
    now = datetime.now(timezone.utc)
    
    trade_info = TradeTakenInformation(
        time_bought=now,
        token_bought_snapshot=token,
        buy_market_cap=15000,
        position_size=1.0,
        current_market_cap=30001,  # > +100%
        peak_market_cap=30001,
        current_curve_pct=50.0,
        confidence=50.0
    )
    
    reason = baseline_strategy._check_for_sl_tp(trade_info)
    assert reason is not None
    assert reason.category == SellCategory.TAKE_PROFIT
    assert "Fixed Take Profit" in reason.details

def test_risk_check_sl_tp_hits_stop_loss(baseline_strategy):
    token = create_mock_token()
    now = datetime.now(timezone.utc)
    
    trade_info = TradeTakenInformation(
        time_bought=now,
        token_bought_snapshot=token,
        buy_market_cap=15000,
        position_size=1.0,
        current_market_cap=11000,  # < -25%
        peak_market_cap=15000,
        current_curve_pct=50.0,
        confidence=50.0
    )
    
    reason = baseline_strategy._check_for_sl_tp(trade_info)
    assert reason is not None
    assert reason.category == SellCategory.STOP_LOSS
    assert "Fixed Stop Loss" in reason.details

def test_risk_check_sl_tp_curve_graduation(baseline_strategy):
    token = create_mock_token()
    now = datetime.now(timezone.utc)
    
    trade_info = TradeTakenInformation(
        time_bought=now,
        token_bought_snapshot=token,
        buy_market_cap=15000,
        position_size=1.0,
        current_market_cap=16000,
        peak_market_cap=16000,
        current_curve_pct=99.0, # >= 98.0 config
        confidence=50.0
    )
    
    reason = baseline_strategy._check_for_sl_tp(trade_info)
    assert reason is not None
    assert reason.category == SellCategory.TAKE_PROFIT
    assert "Curve Completion" in reason.details

def test_risk_check_sl_tp_holds_in_range(baseline_strategy):
    token = create_mock_token()
    now = datetime.now(timezone.utc)
    
    trade_info = TradeTakenInformation(
        time_bought=now,
        token_bought_snapshot=token,
        buy_market_cap=15000,
        position_size=1.0,
        current_market_cap=16000, # well within range
        peak_market_cap=16000,
        current_curve_pct=50.0,
        confidence=50.0
    )
    
    reason = baseline_strategy._check_for_sl_tp(trade_info)
    assert reason is None
