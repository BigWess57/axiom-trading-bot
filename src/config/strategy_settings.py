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
    'max_daily_trades': 20,         # Max 20 trades per day

    # Risk Management
    'stop_loss_pct': 0.30,          # 30% stop-loss
    'take_profit_pct': 0.60,        # 60% take-profit
    'sell_at_curve_pct': 0.98,      # 98% sell before graduation (curve percentage)
    'max_holding_time': 60 * 5,     # 5 minutes max hold time
    'max_trades_per_token': 3,      # Max trades per token (re-entry limit)
    'cooldown_minutes': 3,          # Chill time after selling before rebuying same token

    # Safety Checks (Holders)
    'holder_check_count': 30,       # Number of top holders to check
    'min_holder_sol_balance': 1.0,  # Min SOL for top holders to be considered "safe"

    # System Settings
    'enable_tui': False,            # Enable terminal UI
    'enable_dashboard': True,       # Enable dashboard
    

    # Security Checkup Limits
    'max_top10_percent': 50.0,
    'max_dev_holding_percent': 20.0,
    'max_insiders_percent': 30.0,
    'max_bundled_percent': 50.0,
    'min_pro_trader_percent': 20.0,
    'max_volume_fees_ratio': 20000.0,

    # Buy Signal Rules
    'max_token_age_seconds': 600,   # 10 minutes
    'min_market_cap': 9000.0,
    'max_market_cap': 18000.0,

    # Confidence Calculation
    'baseline_confidence_score': 30.0,
    'min_confidence_score': 50.0,
    'good_confidence_score': 70.0,

    'confidence_boost_high_holder_safety': 10.0,
    'confidence_penalty_low_holder_safety': 30.0,
    'confidence_penalty_ath_impact': 20.0,
    'confidence_boost_improving_distribution_ratio': 10.0,
    'confidence_penalty_worsening_distribution_ratio': 10.0,
    
    'holder_safety_threshold_high': 0.66,
    'holder_safety_threshold_low': 0.33,
    'ath_impact_threshold': 0.4,
    'distribution_trend_lookback': 5,
    'activity_lookback_seconds': 60,

    'min_txns_for_boost': 50,
    'confidence_boost_high_activity': 10.0,
    'confidence_boost_buying_pressure': 5.0,
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
    
