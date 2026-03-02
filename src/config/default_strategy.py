"""
Default strategy configuration settings.
These values can be overridden by environment variables or specific deployment configs.
"""
import os

# Default configuration for the FirstTestStrategy
DEFAULT_STRATEGY_CONFIG = {
    # Account Settings
    'starting_balance': 20,         # 20 SOL starting balance
    'fees_percentage': 0.03,        # 3% fees per trade (slippage + network)

    # Position Sizing
    'max_position_size': 1,       # 1 SOL max per trade
    'min_position_size': 0.3,    # 0.3 SOL min per trade
    'max_daily_trades': 20,         # Max 20 trades per day

    # Risk Management
    'stop_loss_pct': 0.30,          # 30% stop-loss
    'take_profit_pct': 0.60,        # 60% take-profit
    'sell_at_curve_pct': 0.98,      # 98% sell before graduation (curve percentage)
    'max_holding_time': 60 * 5,     # 5 minutes max hold time
    'max_trades_per_token': 3,      # Max trades per token (re-entry limit)
    'cooldown_minutes': 3,          # Chill time after selling before rebuying same token

    # Safety Checks (Holders)
    'holder_check_count': 25,       # Number of top holders to check
    'min_holder_sol_balance': 1.0,  # Min SOL for top holders to be considered "safe"

    # System Settings
    'enable_tui': False,            # Enable terminal UI
    'enable_dashboard': True,       # Enable dashboard
    

    # Security Checkup Limits (critical ones)
    'max_top10_percent': 60.0,
    'max_dev_holding_percent': 20.0,
    'max_insiders_percent': 30.0,
    'max_bundled_percent': 60.0,
    'min_pro_trader_percent': 20.0,
    'max_volume_fees_ratio': 20000.0,

    # Buy Signal Rules
    'max_token_age_seconds': 600,   # 10 minutes
    'min_market_cap': 9000.0,
    'max_market_cap': 18000.0,

    # Confidence Calculation

    'baseline_confidence_score': 20.0,
    'min_confidence_score': 50.0,
    'good_confidence_score': 100.0,
    
    ## Holder Safety
    'holder_safety_threshold_high': 0.80,
    'holder_safety_threshold_low': 0.33,
    'confidence_boost_high_holder_safety': 5.0,
    'confidence_penalty_low_holder_safety': 40.0,

    ## Top 10 Holders / Bundled
    'confidence_security_penalty_high': 30.0,
    'security_penalty_threshold': 30.0,

    ## ATH Impact
    'ath_impact_threshold': 0.4,
    'confidence_penalty_ath_impact': 20.0,

    ## Distribution Ratio
    'distribution_trend_lookback': 30,
    'max_distribution_ratio_inc': 0.4,
    'confidence_boost_improving_distribution_ratio': 15.0,

    ## Activity
    'activity_lookback_seconds': 60,

    'min_txns_for_boost': 50,
    'max_txns_inc_for_full_boost': 200,
    'max_buy_sell_ratio_inc_for_full_boost': 3.0,
    'min_users_watching_increase': 20,
    'max_users_watching_inc_for_full_boost': 50,
    'max_kols_inc_for_full_boost': 3,

    'confidence_boost_buying_pressure': 15.0,
    'confidence_boost_high_activity': 15.0,
    'confidence_boost_new_kol': 10.0,
    'confidence_boost_users_watching': 7.0,

    # Hold Confidence Configuration
    'baseline_hold_confidence': 100.0,
    'min_hold_confidence_score': 50.0,
    
    'activity_lookback_short': 30, # short MA (30s)
    'tx_velocity_lookback_long': 120, # long MA to compare against (120s)
    'max_velocity_drop_percent': 0.50, # 50% drop in tx/min is max penalty
    'hold_penalty_velocity_death': 30.0,
    
    'max_holder_drop_percent': 0.30, # 30% of holders leaving is max penalty
    'hold_penalty_holder_exodus': 25.0,
    
    'max_users_watching_drop_percent': 0.30, # 30% drop in viewers is max penalty
    'hold_penalty_hype_death': 15.0,
    
    'max_sell_buy_ratio': 2, # 2 sells per buy is max penalty
    'hold_penalty_sell_pressure': 25.0,
    
    'hold_penalty_safety_breach': 30.0, # Linear penalty for Top 10 or bundled %
}

def get_whole_config():
    """
    Returns the strategy configuration, injecting environment variables where necessary.
    """
    config = DEFAULT_STRATEGY_CONFIG.copy()
    
    # Inject API Keys / Wallet from Env
    config['auth_token'] = os.getenv('AUTH_TOKEN')
    config['refresh_token'] = os.getenv('REFRESH_TOKEN')
    config['wallet_address'] = os.getenv('WALLET_ADDRESS')
    
    return config

def get_strategy_config():
    """
    Returns the strategy configuration, injecting environment variables where necessary.
    """
    config = DEFAULT_STRATEGY_CONFIG.copy()
    
    return config
    
