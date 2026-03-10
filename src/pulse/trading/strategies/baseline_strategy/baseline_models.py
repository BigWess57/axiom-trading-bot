"""
Strategy configuration for baseline trading strategy
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class BaselineAccountConfig:
    starting_balance: float
    fees_percentage: float

@dataclass
class BaselineRiskConfig:
    max_position_size: float
    min_position_size: float
    initial_stop_loss_pct: float
    max_take_profit_pct: float
    sell_at_curve_pct: float
    max_holding_time: int
    max_trades_per_token: int
    cooldown_minutes: int

@dataclass
class BaselineSafetyConfig:
    min_holder_sol_balance: float
    holder_check_count: int
    max_top10_percent: float
    max_dev_holding_percent: float
    max_insiders_percent: float
    max_bundled_percent: float
    min_pro_trader_percent: float
    max_volume_fees_ratio: float
    holder_safe_threshold: float

@dataclass
class BaselineBuyRulesConfig:
    max_token_age_seconds: int
    min_market_cap: float
    max_market_cap: float
    min_txns_per_min: int
    min_buy_sell_ratio: float
    min_users_watching_increase: int
    activity_lookback_seconds: int


class BaselineStrategyConfig:
    """Configuration for baseline trading strategy"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        d = config_dict
        
        try:
            self.account = BaselineAccountConfig(
                starting_balance=float(d['starting_balance']),
                fees_percentage=float(d['fees_percentage'])
            )
            
            self.risk = BaselineRiskConfig(
                max_position_size=float(d['max_position_size']),
                min_position_size=float(d['min_position_size']),
                initial_stop_loss_pct=float(d['initial_stop_loss_pct']),
                max_take_profit_pct=float(d['max_take_profit_pct']),
                sell_at_curve_pct=float(d['sell_at_curve_pct']),
                max_holding_time=int(d['max_holding_time']),
                max_trades_per_token=int(d['max_trades_per_token']),
                cooldown_minutes=int(d['cooldown_minutes'])
            )
            
            self.safety = BaselineSafetyConfig(
                min_holder_sol_balance=float(d['min_holder_sol_balance']),
                holder_check_count=int(d['holder_check_count']),
                max_top10_percent=float(d['max_top10_percent']),
                max_dev_holding_percent=float(d['max_dev_holding_percent']),
                max_insiders_percent=float(d['max_insiders_percent']),
                max_bundled_percent=float(d['max_bundled_percent']),
                min_pro_trader_percent=float(d['min_pro_trader_percent']),
                max_volume_fees_ratio=float(d['max_volume_fees_ratio']),
                holder_safe_threshold=float(d.get('holder_safe_threshold', 0.33))
            )
            
            self.buy_rules = BaselineBuyRulesConfig(
                max_token_age_seconds=int(d['max_token_age_seconds']),
                min_market_cap=float(d['min_market_cap']),
                max_market_cap=float(d['max_market_cap']),
                min_txns_per_min=int(d['min_txns_per_min']),
                min_buy_sell_ratio=float(d['min_buy_sell_ratio']),
                min_users_watching_increase=int(d['min_users_watching_increase']),
                activity_lookback_seconds=int(d['activity_lookback_seconds'])
            )
            
        except KeyError as e:
            raise ValueError(f"Missing required strategy configuration key: {e}") from e
