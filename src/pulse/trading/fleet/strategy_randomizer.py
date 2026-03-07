import random
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG

logger = logging.getLogger("StrategyRandomizer")

class StrategyRandomizer:
    """Utility to generate randomized strategy configurations for the Shadow Fleet."""

    @staticmethod
    def generate_randomized_configs(num_configs: int) -> Dict[str, Dict[str, Any]]:
        """
        Generates a list of randomized configuration dictionaries based on the default config.
        Returns a dictionary with the strategy id as the key and the config as the value.
        """
        configs = {}
        for i in range(num_configs):
            conf = DEFAULT_STRATEGY_CONFIG.copy()

            # --- Risk Parameters ---
            # Stop Loss: 10% to 50%
            conf["initial_stop_loss_pct"] = round(random.uniform(0.20, 0.40), 2)
            # Take Profit: 20% to 150%
            conf["max_take_profit_pct"] = round(random.uniform(1.20, 2.00), 2)
            # Max Holding Time: 1 to 10 minutes (60 to 600 seconds)
            conf["max_holding_time"] = random.randint(120, 600)
            
            # --- Safety Parameters ---
            conf["min_holder_sol_balance"] = round(random.uniform(0.5, 2.0), 1)
            conf["holder_check_count"] = random.choice([20, 25, 30])
            conf["min_pro_trader_percent"] = round(random.uniform(15.0, 30.0), 1)

            # --- Buy Rules Parameters ---
            # Min Market Cap: 6,000 to 10,000
            conf["min_market_cap"] = round(random.uniform(5500, 8000), 2)
            # Max Market Cap: min_market_cap + 5000 to 20,000
            conf["max_market_cap"] = round(random.uniform(17000, 20000), 2)
            
            # --- Confidence Parameters ---
            # Baseline: 10 to 40
            conf["baseline_confidence_score"] = round(random.uniform(10.0, 40.0), 1)
            # Min Score needed: baseline to 70
            conf["min_confidence_score"] = round(random.uniform(conf["baseline_confidence_score"], 70.0), 1)

            # Holder Safety
            conf["holder_safety_threshold_high"] = round(random.uniform(0.60, 0.90), 2)
            conf["holder_safety_threshold_low"] = round(random.uniform(0.20, 0.40), 2)
            conf["confidence_boost_high_holder_safety"] = round(random.uniform(2.0, 10.0), 1)
            conf["confidence_penalty_low_holder_safety"] = round(random.uniform(20.0, 50.0), 1)

            # Top 10 Holders / Bundled
            conf["confidence_security_penalty_high"] = round(random.uniform(15.0, 40.0), 1)
            conf["security_penalty_threshold"] = round(random.uniform(20.0, 50.0), 1)

            # ATH Impact
            conf["ath_impact_threshold"] = round(random.uniform(0.20, 0.45), 2)
            conf["confidence_penalty_ath_impact"] = round(random.uniform(10.0, 30.0), 1)

            # Distribution Ratio
            conf["distribution_trend_lookback"] = random.randint(10, 60)
            conf["max_distribution_ratio_inc"] = round(random.uniform(0.2, 0.6), 2)
            conf["confidence_boost_improving_distribution_ratio"] = round(random.uniform(5.0, 25.0), 1)

            # Activity
            conf["activity_lookback_seconds"] = random.choice([30, 45, 60, 90, 120])
            conf["min_txns_per_min_for_boost"] = random.randint(20, 100)
            conf["max_txns_per_min_inc_for_full_boost"] = random.randint(100, 400)
            conf["max_buy_sell_ratio_inc_for_full_boost"] = round(random.uniform(1.5, 5.0), 1)
            conf["min_users_watching_increase"] = random.randint(5, 40)
            conf["max_users_watching_inc_for_full_boost"] = random.randint(30, 100)
            conf["max_kols_inc_for_full_boost"] = random.randint(2, 3)

            conf["confidence_boost_buying_pressure"] = round(random.uniform(5.0, 25.0), 1)
            conf["confidence_boost_high_activity"] = round(random.uniform(5.0, 25.0), 1)
            conf["confidence_boost_new_kol"] = round(random.uniform(5.0, 20.0), 1)
            conf["confidence_boost_users_watching"] = round(random.uniform(3.0, 12.0), 1)

            # --- Hold Confidence Parameters ---
            conf["min_hold_confidence_score"] = round(random.uniform(30.0, 50.0), 1)
            
            conf["activity_lookback_short"] = random.choice([15, 30, 45])
            conf["tx_velocity_lookback_long"] = random.choice([60, 90, 120, 180])
            conf["max_velocity_drop_percent"] = round(random.uniform(0.30, 0.70), 2)
            conf["hold_penalty_velocity_death"] = round(random.uniform(15.0, 35.0), 1)
            
            conf["max_holder_drop_percent"] = round(random.uniform(0.15, 0.50), 2)
            conf["hold_penalty_holder_exodus"] = round(random.uniform(15.0, 30.0), 1)
            
            conf["max_users_watching_drop_percent"] = round(random.uniform(0.15, 0.50), 2)
            conf["hold_penalty_hype_death"] = round(random.uniform(10.0, 25.0), 1)
            
            conf["max_sell_buy_ratio"] = round(random.uniform(1.5, 3.5), 1)
            conf["hold_penalty_sell_pressure"] = round(random.uniform(10.0, 35.0), 1)
            
            conf["hold_penalty_safety_breach"] = round(random.uniform(20.0, 50.0), 1)
            
            # Add a unique identifier based on key params to the dict
            bot_id = f"Bot_{i:03d}"

            configs[bot_id] = conf
            
        # Save to lookup table on disk
        log_dir = Path("data/config_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_path = log_dir / f"fleet_configs_{timestamp}.json"
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=4)
            
        logger.info(f"Generated {num_configs} strategy configs and saved map to {config_path}")

        return configs
