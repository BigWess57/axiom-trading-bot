# Baseline Trading Strategy Documentation

This document describes the "Baseline" simplistic trading strategy designed to serve as the foundational benchmark for the Shadow Fleet. The goal is to isolate strict security rules and basic momentum indicators while removing all complex, overlapping logic (such as dynamic position sizing, complex confidence scoring, holder trend analysis, and trailing stop losses).
The more complex strategy will be added later, little by little.

## 1. Core Philosophy
Keep the strict anti-rug security checks, but strip the entry and exit logic down to the bare minimum. The strategy evaluates raw momentum (speed and hype) on safe contracts and exits with fixed mathematical bounds to ascertain raw edge expectancy.

## 2. Bot Configuration Parameters (Baseline)

| Parameter | Value (Recommendation) | Description |
| :--- | :--- | :--- |
| **Position Size** | `1 SOL` (Fixed) | Static position size per trade. No dynamic scaling. |
| **Max Active Trades** | `5` | Maximum concurrent trades. |
| **Cooldown** | `3 minutes` | Time to wait before executing a new trade on a previously sold token. |
| **Max Trades Per Token**| `3` | Stop trading a token after 3 trips. |

### 2.1 Security Parameters (Strict Mode)
These remain unchanged from the complex strategy to guarantee capital preservation against obvious rug pulls.
- **Top 10 Holders:** `<= 50%`
- **Dev Holding:** `<= 20%`
- **Insiders:** `<= 30%`
- **Bundled Supply:** `<= 50%`
- **Holders:** `> 0`
- **Fees Paid:** `> 0`
- **Pro Traders:** `>= 20%` of total holders (if holders > 0)
- **Volume/Fees Ratio:** `Volume / Fees <= 20,000`
- **Holder Safety Metric:** At least `40%` of the top 25 holders must have a SOL balance `>= 1.0 SOL`.

### 2.2 Entry Parameters (Momentum Scalper)
All complex `buy_confidence` calculations are removed. A token triggers a BUY if it passes security and meets these raw thresholds:
- **Maximum Age:** `< 10 minutes` (Fast execution on new tokens)
- **Market Cap:** `Between $6,000 and $18,000`
- **Transaction Velocity:** `> 50 transactions` in the dynamic lookback window (default 60s).
- **Buying Pressure:** `Buys/Sells ratio > 1.5` in the dynamic lookback window.
- **Hype Metric:** `Active Users Watching` count must have increased by `> 50` users during the lookback window.

*(Note: "ATH Impact", "Holder Distributions", and "KOL tracking" are completely removed from this baseline.)*

### 2.3 Exit Parameters (Fixed Bounds)
All complex `hold_confidence`, Time-Based Exits, Bonding Curve limits, and Trailing Stops are explicitly disabled. 
- **Fixed Stop Loss (SL):** `-25%` from entry Market Cap.
- **Fixed Take Profit (TP):** `+100%` from entry Market Cap.
- **Curve Graduation Constraint:** Explicitly sell if token reaches `98%` of the Raydium bonding curve to avoid migration mechanics.
- **Token Removed:** Immediate market sell if token is removed from tracking category.

## 3. Data Requirements & API Calls
By removing the `ATH Impact` check and the complex distribution tracker, the bot **does not** need to make blocking API calls to fetch historical ATH data upon discovering a new token. It relies purely on the live data stream.

## 4. Evaluation Protocol in Shadow Fleet
This strategy is to be tested extensively in the Shadow Fleet. The core success metric is the isolated Win/Loss ratio. Since the R/R is explicitly fixed at 1:4 (risk 25% to make 100%), the strategy needs a win rate > 20% to break even before fees, and slightly higher to cover them.
