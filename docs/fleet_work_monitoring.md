# Fleet Work Monitoring

## Overview
This document serves as a historical record of the optimizations and enhancements applied to the Shadow Fleet architecture based on the designs in `2026-02-22-fleet-optimization-design.md`.

## Implemented Enhancements

### 1. Strategy Randomizer (`strategy_randomizer.py`)
- Created a robust generator capable of producing hundreds of unique strategy configurations based on `DEFAULT_STRATEGY_CONFIG`.
- **Randomized Parameters:**
  - Risk: `stop_loss_pct`, `take_profit_pct`, `max_holding_time`
  - Buy Rules: `min_market_cap`, `max_market_cap`
  - Confidence Baselines: `baseline_confidence_score`, `min_confidence_score`, `good_confidence_score` 
  - Confidence Boosts & Penalties: Holder safety penalties, ATH impact penalties, distribution ratio adjustments, buying pressure.
  - Evaluation Lookbacks & Thresholds: `distribution_trend_lookback`, `activity_lookback_seconds`, `holder_safety_threshold_high/low`.
- **Fixed Parameters:** Security-critical thresholds (insider percentage, top 10 percent, volume/fees ratio) remain static to prevent catastrophic losses to honeypots/rugs.

### 2. Fleet Configuration Lookup Table
- To keep terminal outputs and CSV files clean, the generator assigns deterministic, short IDs to bots (e.g., `Bot_042`).
- The entire dictionary of randomized parameters for a session is dumped into `data/config_logs/fleet_configs_{timestamp}.json` before the fleet begins listening to the market.

### 3. Analytics Script (`analyze_fleet.py`)
- Built an analysis tool to parse the massive `shadow_trades_{timestamp}.csv` files.
- **Run Command:**
  ```bash
  PYTHONPATH=. python3 src/pulse/scripts/analyze_fleet.py <PATH_TO_CSV> --min_trades 10 --top_n 20 --configs_path <PATH_TO_CONFIG_JSON> 
  ```
  (example: PYTHONPATH=. python3 src/pulse/scripts/analyze_fleet.py data/shadow_logs/shadow_trades_20260224_005134.csv --min_trades 20 --top_n 20 --configs_path data/config_logs/fleet_configs_20260224_005134.json)
- **Filtering & Ranking:**
  - Enforces statistical significance (drops bots with fewer than `X` trades, defaulting to 10).
  - Ranks surviving bots by **Total Realized PnL**.
- **Lookup Integration:**
  - Ingests the corresponding `fleet_configs_{timestamp}.json` file.
  - Automatically prints the exact configuration parameters of the top-performing bots directly inside the terminal report.

### 4. CSV Size Optimization (`shadow_recorder.py`)
- Identified a massive bottleneck where the entire 45-field Token Snapshot (including holders and timestamps) was being serialized into a JSON string and saved on *every single trade* across *every single bot*.
- **Fix:** Removed the `token_snapshot_json` from the CSV output entirely, resulting in an ~85% reduction in log file size.

### 5. Graduation Handling (Pump.fun -> Raydium)
- **Problem:** Bots were holding tokens too long and failing to track PnL properly when tokens graduated off the bonding curve.
- **Solution (Dynamic TP Capping):** 
  - Added `current_curve_pct` to the live `TradeTakenInformation`.
  - Added `sell_at_curve_pct` to the Strategy Risk Config (defaulted to 98%).
  - Forced a `Take Profit` exit condition the moment the bonding curve hits the threshold, safely exiting positions before Raydium migration.
