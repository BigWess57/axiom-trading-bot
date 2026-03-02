import random
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG

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
            conf["stop_loss_pct"] = round(random.uniform(0.10, 0.50), 2)
            # Take Profit: 20% to 150%
            conf["take_profit_pct"] = round(random.uniform(0.20, 1.50), 2)
            # Max Holding Time: 1 to 10 minutes (60 to 600 seconds)
            conf["max_holding_time"] = random.randint(60, 600)
            
            # --- Safety Parameters ---
            conf["min_holder_sol_balance"] = round(random.uniform(0.5, 2.0), 1)
            conf["holder_check_count"] = random.choice([20, 30, 40, 50])
            conf["max_top10_percent"] = round(random.uniform(30.0, 60.0), 1)
            conf["max_insiders_percent"] = round(random.uniform(20.0, 40.0), 1)
            conf["max_bundled_percent"] = round(random.uniform(30.0, 60.0), 1)
            conf["min_pro_trader_percent"] = round(random.uniform(15.0, 30.0), 1)
            conf["max_volume_fees_ratio"] = round(random.uniform(10000.0, 25000.0), 1)

            # --- Buy Rules Parameters ---
            # Min Market Cap: 6,000 to 10,000
            conf["min_market_cap"] = round(random.uniform(6000, 10000), 2)
            # Max Market Cap: min_market_cap + 5000 to 20,000
            conf["max_market_cap"] = round(random.uniform(conf["min_market_cap"] + 5000, 20000), 2)
            
            # --- Confidence Parameters ---
            # Baseline: 20 to 50
            conf["baseline_confidence_score"] = round(random.uniform(20.0, 50.0), 1)
            # Min Score needed: baseline to 80
            conf["min_confidence_score"] = round(random.uniform(conf["baseline_confidence_score"], 80.0), 1)
            # Good Score needed: min_score to 95
            conf["good_confidence_score"] = round(random.uniform(conf["min_confidence_score"], 95.0), 1)

            # Boosts & Penalties
            conf["confidence_penalty_ath_impact"] = round(random.uniform(10.0, 30.0), 1)
            conf["confidence_boost_improving_distribution_ratio"] = round(random.uniform(5.0, 15.0), 1)
            conf["confidence_boost_high_activity"] = round(random.uniform(5.0, 25.0), 1)
            conf["confidence_boost_buying_pressure"] = round(random.uniform(5.0, 20.0), 1)
            
            # Thresholds
            conf["holder_safety_threshold_high"] = round(random.uniform(0.60, 0.85), 2)
            conf["holder_safety_threshold_low"] = round(random.uniform(0.30, 0.50), 2)
            conf["ath_impact_threshold"] = round(random.uniform(0.20, 0.60), 2)
            conf["min_txns_for_boost"] = random.randint(20, 100)
            
            # Lookbacks
            conf["distribution_trend_lookback"] = random.randint(5, 20)
            conf["activity_lookback_seconds"] = random.choice([30, 45, 60, 90, 120])
            
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
            
        print(f"Generated {num_configs} strategy configs and saved map to {config_path}")

        return configs
