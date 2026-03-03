import pytest
from datetime import datetime, timezone, timedelta
from src.pulse.types import SellCategory
from __tests__.conftest import make_token, make_trade_info, make_strategy, make_state

SOL = 150.0

@pytest.fixture
def strategy():
    return make_strategy(
        sol_price=SOL,
        initial_stop_loss_pct=0.30,
        late_entry_rr_ratio=2.0,
        max_take_profit_pct=1.50,
        trailing_step_buffer_pct=0.20,
        confidence_caution_threshold=70.0,
        sell_at_curve_pct=0.98,
        max_holding_time=300,
    )

def test_late_entry_dynamic_scaling(strategy):
    # Buy close to graduation. 
    # Let's say graduation is $69,000 (roughly 100% curve in old linear math).
    # Target curve is 0.98 (98%).
    # If we buy at $50,000 (roughly 72.46% of curve), our max profit is NOT just linear (69k / 50k = 38%).
    # We showed via the CPAMM simulation that 70% curve is 248 MC, and 98% curve is 398 MC.
    # Therefore the expected profit multiplier is parabolic.
    # The actual algorithm computed exactly: 53.02%
    buy_mc = 50000.0
    token = make_token(market_cap=buy_mc / SOL, category="finalStretch")
    
    # We simulate curve pct at entry to be 72.46%
    trade = make_trade_info(token=token, buy_market_cap=buy_mc, current_curve_pct=72.46)
    
    # First tick to initialize the fixed bounds
    strategy.should_sell(trade, make_state(trade.token_bought_snapshot))
    
    # Verify it locked in LATE ENTRY values
    assert trade.fixed_take_profit_pct is not None
    assert trade.fixed_stop_loss_pct is not None
    
    # Expected TP = 53.02%
    # Expected SL = 53.02% / 2.0 = 26.51%
    assert 0.53 < trade.fixed_take_profit_pct < 0.54
    assert 0.26 < trade.fixed_stop_loss_pct < 0.27

    # Verify that a drop triggers SL exactly
    current_mc_sl = buy_mc * (1 - trade.fixed_stop_loss_pct) - 1.0 # 1 dollar below sl
    trade.current_market_cap = current_mc_sl
    
    reason = strategy.should_sell(trade, make_state(trade.token_bought_snapshot))
    assert reason is not None
    assert reason.category == SellCategory.STOP_LOSS


def test_early_entry_confidence_trailing(strategy):
    from unittest.mock import patch
    
    # Buy very early. Plenty of room.
    buy_mc = 10000.0
    token = make_token(market_cap=buy_mc / SOL, category="finalStretch")
    trade = make_trade_info(token=token, buy_market_cap=buy_mc, current_curve_pct=10.0)
    
    state = make_state(trade.token_bought_snapshot)
    
    # 1. Set high confidence > 70
    with patch.object(strategy, '_calculate_hold_confidence', return_value=80.0):
        # Price goes up +50% to $15,000.
        trade.current_market_cap = 15000.0
        reason = strategy.should_sell(trade, state)
        
        # Should not sell. Peak market cap should register as 15000.
        assert reason is None
        assert trade.peak_market_cap == 15000.0
        
        # Since confidence is 80 (high), the SL is still the initial 30% from entry ($7,000).
        # Even if price drops to $11,000 (which is > 20% drop from 15k), we DO NOT trail yet!
        trade.current_market_cap = 11000.0
        reason = strategy.should_sell(trade, state)
        assert reason is None
        
    # 2. Confidence drops to 60 (Caution!)
    with patch.object(strategy, '_calculate_hold_confidence', return_value=60.0):
        # We bounce the price back to $15k to trigger the logic check while confidence is low
        trade.current_market_cap = 15000.0
        reason = strategy.should_sell(trade, state)
        assert reason is None
        
        # The strategy has now locked in a trailing SL at $12k (20% below $15k peak).
        
    # 3. Confidence Bounces Back to 90 (Strong Buy)
    with patch.object(strategy, '_calculate_hold_confidence', return_value=90.0):
        # Price drops to $11,000. Even though confidence is massive, the trailing SL
        # remains ratcheted at $12k permanently.
        trade.current_market_cap = 11000.0
        reason = strategy.should_sell(trade, state)
        assert reason is not None
        assert reason.category == SellCategory.STOP_LOSS
        assert "Trailing" in reason.details
