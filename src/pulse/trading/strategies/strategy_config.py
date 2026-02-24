"""
Strategy configuration for trading strategies
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AccountConfig:
    """Account configuration"""
    starting_balance: float = 20.0
    fees_percentage: float = 0.03
    enable_tui: bool = False
    enable_dashboard: bool = True

@dataclass
class RiskConfig:
    """Risk configuration"""
    max_position_size: float = 1.0
    max_daily_trades: int = 20
    stop_loss_pct: float = 0.30
    take_profit_pct: float = 0.60
    sell_at_curve_pct: float = 0.98
    max_holding_time: int = 300
    max_trades_per_token: int = 3
    cooldown_minutes: int = 3

@dataclass
class SafetyConfig:
    """Safety configuration"""
    min_holder_sol_balance: float = 1.0
    holder_check_count: int = 30
    max_top10_percent: float = 50.0
    max_dev_holding_percent: float = 20.0
    max_insiders_percent: float = 30.0
    max_bundled_percent: float = 50.0
    min_pro_trader_percent: float = 20.0
    max_volume_fees_ratio: float = 20000.0

@dataclass
class BuyRulesConfig:
    """Buy rules configuration"""
    max_token_age_seconds: int = 600
    min_market_cap: float = 9000.0
    max_market_cap: float = 18000.0

@dataclass
class ConfidenceConfig:
    """Confidence configuration"""
    baseline_confidence_score: float = 30.0
    min_confidence_score: float = 50.0
    good_confidence_score: float = 70.0
    
    # Weights & Thresholds
    confidence_boost_high_holder_safety: float = 10.0
    confidence_penalty_low_holder_safety: float = 30.0
    
    confidence_boost_improving_distribution_ratio: float = 10.0
    confidence_penalty_worsening_distribution_ratio: float = 10.0
    
    holder_safety_threshold_high: float = 0.66
    holder_safety_threshold_low: float = 0.33
    ath_impact_threshold: float = 0.4
    confidence_penalty_ath_impact: float = 20.0
    distribution_trend_lookback: int = 5
    activity_lookback_seconds: int = 60

    
    min_txns_for_boost: int = 50
    confidence_boost_high_activity: float = 10.0
    confidence_boost_buying_pressure: float = 10.0


class StrategyConfig:
    """Configuration for trading strategies, organized by category"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize the configuration from a dictionary (flat or nested).
        Handles mapping flat keys to nested config objects.
        """
        # Helper to safely get value with default fallback if needed, 
        # though we expect config_dict to be populated from defaults.
        d = config_dict
        
        self.account = AccountConfig(
            starting_balance=d.get('starting_balance', 20.0),
            fees_percentage=d.get('fees_percentage', 0.03),
            enable_tui=d.get('enable_tui', False),
            enable_dashboard=d.get('enable_dashboard', True)
        )
        
        self.risk = RiskConfig(
            max_position_size=d.get('max_position_size', 1.0),
            max_daily_trades=d.get('max_daily_trades', 20),
            stop_loss_pct=d.get('stop_loss_pct', 0.30),
            take_profit_pct=d.get('take_profit_pct', 0.60),
            sell_at_curve_pct=d.get('sell_at_curve_pct', 0.98),
            max_holding_time=d.get('max_holding_time', 300),
            max_trades_per_token=d.get('max_trades_per_token', 3),
            cooldown_minutes=d.get('cooldown_minutes', 3)
        )
        
        self.safety = SafetyConfig(
            min_holder_sol_balance=d.get('min_holder_sol_balance', 1.0),
            holder_check_count=d.get('holder_check_count', 30),
            max_top10_percent=d.get('max_top10_percent', 50.0),
            max_dev_holding_percent=d.get('max_dev_holding_percent', 20.0),
            max_insiders_percent=d.get('max_insiders_percent', 30.0),
            max_bundled_percent=d.get('max_bundled_percent', 50.0),
            min_pro_trader_percent=d.get('min_pro_trader_percent', 20.0),
            max_volume_fees_ratio=d.get('max_volume_fees_ratio', 20000.0)
        )
        
        self.buy_rules = BuyRulesConfig(
            max_token_age_seconds=d.get('max_token_age_seconds', 600),
            min_market_cap=d.get('min_market_cap', 9000.0),
            max_market_cap=d.get('max_market_cap', 18000.0)
        )
        
        self.confidence = ConfidenceConfig(
            baseline_confidence_score=d.get('baseline_confidence_score', 30.0),
            min_confidence_score=d.get('min_confidence_score', 50.0),
            good_confidence_score=d.get('good_confidence_score', 70.0),
            confidence_boost_high_holder_safety=d.get('confidence_boost_high_holder_safety', 10.0),
            confidence_penalty_low_holder_safety=d.get('confidence_penalty_low_holder_safety', 30.0),
            confidence_boost_improving_distribution_ratio=d.get('confidence_boost_improving_distribution_ratio', 10.0),
            confidence_penalty_worsening_distribution_ratio=d.get('confidence_penalty_worsening_distribution_ratio', 10.0),
            holder_safety_threshold_high=d.get('holder_safety_threshold_high', 0.66),
            holder_safety_threshold_low=d.get('holder_safety_threshold_low', 0.33),
            ath_impact_threshold=d.get('ath_impact_threshold', 0.4),
            distribution_trend_lookback=d.get('distribution_trend_lookback', 5),
            min_txns_for_boost=d.get('min_txns_for_boost', 50),
            activity_lookback_seconds=d.get('activity_lookback_seconds', 60),
            confidence_boost_high_activity=d.get('confidence_boost_high_activity', 10.0),
            confidence_boost_buying_pressure=d.get('confidence_boost_buying_pressure', 10.0)
        )
