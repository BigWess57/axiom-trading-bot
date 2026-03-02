"""
Strategy configuration for trading strategies
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AccountConfig:
    """Account configuration"""
    starting_balance: float
    fees_percentage: float
    enable_tui: bool
    enable_dashboard: bool

@dataclass
class RiskConfig:
    """Risk configuration"""
    max_position_size: float
    min_position_size: float
    max_daily_trades: int
    stop_loss_pct: float
    take_profit_pct: float
    sell_at_curve_pct: float
    max_holding_time: int
    max_trades_per_token: int
    cooldown_minutes: int

@dataclass
class SafetyConfig:
    """Safety configuration"""
    min_holder_sol_balance: float
    holder_check_count: int
    max_top10_percent: float
    max_dev_holding_percent: float
    max_insiders_percent: float
    max_bundled_percent: float
    min_pro_trader_percent: float
    max_volume_fees_ratio: float

@dataclass
class BuyRulesConfig:
    """Buy rules configuration"""
    max_token_age_seconds: int
    min_market_cap: float
    max_market_cap: float

@dataclass
class ConfidenceConfig:
    """Confidence configuration"""
    baseline_confidence_score: float
    min_confidence_score: float
    good_confidence_score: float
    
    # Holder Safety
    holder_safety_threshold_high: float
    holder_safety_threshold_low: float
    confidence_boost_high_holder_safety: float
    confidence_penalty_low_holder_safety: float

    # Top 10 Holders / Bundled
    confidence_security_penalty_high: float
    security_penalty_threshold: float

    # ATH Impact
    ath_impact_threshold: float
    confidence_penalty_ath_impact: float

    # Distribution Ratio
    distribution_trend_lookback: int
    max_distribution_ratio_inc: float
    confidence_boost_improving_distribution_ratio: float

    # Activity
    activity_lookback_seconds: int

    max_txns_inc_for_full_boost: int
    max_buy_sell_ratio_inc_for_full_boost: float
    max_users_watching_inc_for_full_boost: int
    max_kols_inc_for_full_boost: int
    min_txns_for_boost: int
    min_users_watching_increase: int

    confidence_boost_buying_pressure: float
    confidence_boost_high_activity: float
    confidence_boost_new_kol: float
    confidence_boost_users_watching: float


@dataclass
class HoldConfidenceConfig:
    baseline_hold_confidence: float
    min_hold_confidence_score: float
    
    activity_lookback_short: int
    tx_velocity_lookback_long: int
    max_velocity_drop_percent: float
    hold_penalty_velocity_death: float
    
    max_holder_drop_percent: float
    hold_penalty_holder_exodus: float
    
    max_users_watching_drop_percent: float
    hold_penalty_hype_death: float
    
    max_sell_buy_ratio: float
    hold_penalty_sell_pressure: float
    
    hold_penalty_safety_breach: float


class StrategyConfig:
    """Configuration for trading strategies, organized by category"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize the configuration from a dictionary (flat or nested).
        Handles mapping flat keys to nested config objects.
        Raises ValueError if any required key is missing.
        """
        d = config_dict
        
        try:
            self.account = AccountConfig(
                starting_balance=float(d['starting_balance']),
                fees_percentage=float(d['fees_percentage']),
                enable_tui=bool(d['enable_tui']),
                enable_dashboard=bool(d['enable_dashboard'])
            )
            
            self.risk = RiskConfig(
                max_position_size=float(d['max_position_size']),
                min_position_size=float(d['min_position_size']),
                max_daily_trades=int(d['max_daily_trades']),
                stop_loss_pct=float(d['stop_loss_pct']),
                take_profit_pct=float(d['take_profit_pct']),
                sell_at_curve_pct=float(d['sell_at_curve_pct']),
                max_holding_time=int(d['max_holding_time']),
                max_trades_per_token=int(d['max_trades_per_token']),
                cooldown_minutes=int(d['cooldown_minutes'])
            )
            
            self.safety = SafetyConfig(
                min_holder_sol_balance=float(d['min_holder_sol_balance']),
                holder_check_count=int(d['holder_check_count']),
                max_top10_percent=float(d['max_top10_percent']),
                max_dev_holding_percent=float(d['max_dev_holding_percent']),
                max_insiders_percent=float(d['max_insiders_percent']),
                max_bundled_percent=float(d['max_bundled_percent']),
                min_pro_trader_percent=float(d['min_pro_trader_percent']),
                max_volume_fees_ratio=float(d['max_volume_fees_ratio'])
            )
            
            self.buy_rules = BuyRulesConfig(
                max_token_age_seconds=int(d['max_token_age_seconds']),
                min_market_cap=float(d['min_market_cap']),
                max_market_cap=float(d['max_market_cap'])
            )
            
            self.confidence = ConfidenceConfig(
                baseline_confidence_score=float(d['baseline_confidence_score']),
                min_confidence_score=float(d['min_confidence_score']),
                good_confidence_score=float(d['good_confidence_score']),
                
                # Holder Safety
                holder_safety_threshold_high=float(d['holder_safety_threshold_high']),
                holder_safety_threshold_low=float(d['holder_safety_threshold_low']),
                confidence_boost_high_holder_safety=float(d['confidence_boost_high_holder_safety']),
                confidence_penalty_low_holder_safety=float(d['confidence_penalty_low_holder_safety']),

                # Top 10 Holders / Bundled
                confidence_security_penalty_high=float(d['confidence_security_penalty_high']),
                security_penalty_threshold=float(d['security_penalty_threshold']),

                # ATH Impact
                ath_impact_threshold=float(d['ath_impact_threshold']),
                confidence_penalty_ath_impact=float(d['confidence_penalty_ath_impact']),

                # Distribution Ratio
                distribution_trend_lookback=int(d['distribution_trend_lookback']),
                max_distribution_ratio_inc=float(d['max_distribution_ratio_inc']),
                confidence_boost_improving_distribution_ratio=float(d['confidence_boost_improving_distribution_ratio']),

                # Activity
                activity_lookback_seconds=int(d['activity_lookback_seconds']),

                max_txns_inc_for_full_boost=int(d['max_txns_inc_for_full_boost']),
                max_buy_sell_ratio_inc_for_full_boost=float(d['max_buy_sell_ratio_inc_for_full_boost']),
                max_users_watching_inc_for_full_boost=int(d['max_users_watching_inc_for_full_boost']),
                max_kols_inc_for_full_boost=int(d['max_kols_inc_for_full_boost']),
                min_txns_for_boost=int(d['min_txns_for_boost']),
                min_users_watching_increase=int(d['min_users_watching_increase']),

                confidence_boost_buying_pressure=float(d['confidence_boost_buying_pressure']),
                confidence_boost_high_activity=float(d['confidence_boost_high_activity']),
                confidence_boost_new_kol=float(d['confidence_boost_new_kol']),
                confidence_boost_users_watching=float(d['confidence_boost_users_watching'])
            )
            
            self.hold_confidence = HoldConfidenceConfig(
                baseline_hold_confidence=float(d['baseline_hold_confidence']),
                min_hold_confidence_score=float(d['min_hold_confidence_score']),
                activity_lookback_short=int(d['activity_lookback_short']),
                tx_velocity_lookback_long=int(d['tx_velocity_lookback_long']),
                max_velocity_drop_percent=float(d['max_velocity_drop_percent']),
                hold_penalty_velocity_death=float(d['hold_penalty_velocity_death']),
                max_holder_drop_percent=float(d['max_holder_drop_percent']),
                hold_penalty_holder_exodus=float(d['hold_penalty_holder_exodus']),
                max_users_watching_drop_percent=float(d['max_users_watching_drop_percent']),
                hold_penalty_hype_death=float(d['hold_penalty_hype_death']),
                max_sell_buy_ratio=float(d['max_sell_buy_ratio']),
                hold_penalty_sell_pressure=float(d['hold_penalty_sell_pressure']),
                hold_penalty_safety_breach=float(d['hold_penalty_safety_breach'])
            )
        except KeyError as e:
            raise ValueError(f"Missing required strategy configuration key: {e}")
