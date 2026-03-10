"""
Baseline strategy configuration settings.
These values provide a stripped-down momentum-focused strategy.
"""
import os

BASELINE_STRATEGY_CONFIG = {
    # Account Settings
    'starting_balance': 20,         # 20 SOL starting balance
    'fees_percentage': 0.03,        # 3% fees per trade (slippage + network)

    # Position Sizing
    'max_position_size': 1.0,       # 1 SOL max per trade
    'min_position_size': 1.0,       # 1 SOL min per trade

    # Risk Management (Fixed bounds)
    'initial_stop_loss_pct': 0.25,  # 25% stop-loss
    'max_take_profit_pct': 1.00,    # 100% take profit
    'sell_at_curve_pct': 0.98,      # 98% sell before graduation (curve percentage)
    'max_holding_time': 60 * 5,     # 5 minutes max hold time
    'max_trades_per_token': 3,      # Max trades per token (re-entry limit)
    'cooldown_minutes': 3,          # Chill time after selling before rebuying same token

    # Safety Checks (Holders)
    'holder_check_count': 25,       # Number of top holders to check
    'min_holder_sol_balance': 1.0,  # Min SOL for top holders to be considered "safe"
    'max_top10_percent': 50.0,
    'max_dev_holding_percent': 20.0,
    'max_insiders_percent': 30.0,
    'max_bundled_percent': 50.0,
    'min_pro_trader_percent': 20.0,
    'max_volume_fees_ratio': 20000.0,
    'holder_safe_threshold': 0.4, # simplified threshold for security check

    # Buy Signal Rules
    'max_token_age_seconds': 600,   # 10 minutes
    'min_market_cap': 6000.0,
    'max_market_cap': 18000.0,
    
    # Momentum Rules
    'min_txns_per_min': 50,
    'min_buy_sell_ratio': 1.5,
    'min_users_watching_increase': 50, # > baseline threshold 
    'activity_lookback_seconds': 60,   # Lookback window for momentum metrics
}

def get_baseline_config():
    """
    Returns the baseline strategy configuration, injecting environment variables where necessary.
    """
    config = BASELINE_STRATEGY_CONFIG.copy()
    
    # Inject API Keys / Wallet from Env
    config['auth_token'] = os.getenv('AUTH_TOKEN')
    config['refresh_token'] = os.getenv('REFRESH_TOKEN')
    config['wallet_address'] = os.getenv('WALLET_ADDRESS')
    
    return config
