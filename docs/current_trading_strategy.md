# Current Trading Strategy Documentation

This document details the current trading strategy implemented in `src/pulse/trading/Bots/my_first_bot.py` and `src/pulse/trading/strategies/core_strategy.py`, supported by modular mixins.

## Overview
The bot is designed to trade tokens on the Pulse platform, focusing on the "First Test" strategy. It monitors token updates, new token listings, and token removals in real-time via WebSocket connections.

## Bot Configuration
Key configuration parameters for the `ExampleTradingBot`:

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Starting Balance** | 20 SOL | Initial balance for simulation. |
| **Max Position Size** | 1 SOL | Maximum amount of SOL to invest per trade. |
| **Fees** | 3% | Estimated fee percentage per trade (buy + sell). |
| **Max Daily Trades** | 20 | Limit on the number of trades executed per day. |
| **Stop Loss** | 30% | Sell if price drops 30% below entry. |
| **Take Profit** | 60% | Sell if price rises 60% above entry. |
| **Max Holding Time** | 5 minutes | Maximum time to hold a position before force selling. |
| **Active Trade Limit** | 5 | Maximum number of concurrent active trades. |
| **Cooldown** | 3 minutes | Time to wait before re-entering a token after selling. |
| **Max Trades Per Token** | 3 | Maximum number of times to trade the same token. |

## Strategy Logic (`CoreStrategy`)

### 1. Buy Logic (`should_buy`)
A token is considered for purchase only if ALL of the following conditions are met:

**A. Category Check**
- The token MUST be in the **"finalStretch"** category.

**B. Security Checks (`_security_checkup`)**
- **Top 10 Holders:** <= 50%
- **Dev Holding:** <= 20%
- **Insiders:** <= 30%
- **Bundled Supply:** <= 50%
- **Holders:** > 0
- **Fees Paid:** > 0
- **Pro Traders:** >= 20% of total holders (if holders > 0)
- **Volume/Fees Ratio:** Volume (USD) / Fees (SOL) <= 20,000

**C. Buy Confidence Score (`_calculate_buy_confidence`)**
- **Baseline Score:** 30
- **Minimum Score required:** 50
- **Good Score:** 100
- **Adjustments (Linear Scaling applied for most):**
    - **Holder Safety:**
        - High Safety (> 66% safe holders): linear boost up to +10.
        - Low Safety (< 33% safe holders): linear penalty up to -30.
    - **Security Penalties:**
        - Top 10 Holders (> 30%): linear penalty up to -20.
        - Bundled Supply (> 30%): linear penalty up to -20.
    - **Chart Health / ATH Impact:**
        - Current Market Cap < 40% of All-Time High: -20
    - **Distribution Trend:**
        - Improving Distribution (MC/Holder ratio decreasing vs weighted historical average): linear boost up to +10.
    - **Activity (Last 30 seconds):**
        - High Transaction velocity (> 3 txns): linear boost up to +15.
        - Buying Pressure (Buys > Sells): linear boost up to +15.
    - **Hype & Attention:**
        - Famous KOLs appearing: +10 per new KOL.
        - Active Users Watching increasing: linear boost up to +10.
- **Position Sizing:**
    - Size is derived linearly from the confidence score.
    - Starts at `min_position_size` (e.g., 0.1 SOL) when at `min_confidence_score` (50).
    - Scales up to `max_position_size` (e.g., 1.0 SOL) when at `good_confidence_score` (100).
    - If score < minimum score, the token is not traded.

**D. Buy Signal Rules (`_check_for_buy_signal`)**
- **Token Age:** < 10 minutes (600 seconds).
- **Market Cap:** Between $9,000 and $18,000 USD.
- **Volume:** Total Volume >= Market Cap.

### 2. Sell Logic (`should_sell`)
The bot evaluates open positions for sell conditions on every token update. A sell is triggered if ANY of the following occur:

**A. Category Change**
- **Reason:** `CATEGORY_CHANGE`
- **Condition:** Token is no longer in the "finalStretch" category.

**B. Security Failure**
- **Reason:** `SECURITY_FAILED`
- **Condition:** Any of the security checks (listed in Buy Logic) fail during the trade.

**C. Stop Loss / Take Profit (`_check_for_sl_tp`)**
- **Stop Loss:**
    - **Reason:** `STOP_LOSS`
    - **Condition:** Current Market Cap < Entry Market Cap * (1 - 0.30)
- **Take Profit:**
    - **Reason:** `TAKE_PROFIT`
    - **Condition:** Current Market Cap > Entry Market Cap * (1 + 0.60)

**D. Hold Confidence (`_calculate_hold_confidence`)**
- **Reason:** `LOW_CONFIDENCE`
- **Condition:** Hold confidence score drops below the minimum threshold (50).
- **Calculation:** Starts at 100 and applies linear penalties during the trade:
    - **Velocity Death:** Penalty up to -30 for a sharp drop in tx velocity from its peak.
    - **Holder Exodus:** Penalty up to -25 if total holders drop from their peak.
    - **Hype Death (Users Watching):** Penalty up to -15 if active viewers drop.
    - **Sell Pressure:** Penalty up to -25 for a high sell/buy ratio in the short term.
    - **Safety Breach:** Penalty up to -30 if Top 10 or Bundled percentages newly exceed safe thresholds.

**E. Time-Based Exit**
- **Reason:** `MAX_HOLD_TIME`
- **Condition:** Position held for longer than **5 minutes** (300 seconds).

**F. Token Removal**
- **Reason:** `TOKEN_REMOVED`
- **Condition:** Token is removed from the tracked category (handled via `on_token_removed` event).

## Execution Workflow

### 1. Token Updates (`on_token_update`)
- **If Not Traded:** Calls `analyze_opportunity`. If `should_buy` returns true and active trades < 5, executes **BUY**.
- **If Currently Traded:** Updates token state and calls `manage_trade`.
    - `manage_trade` calls `should_sell`.
    - If a sell reason is returned, executes **SELL**.

### 2. New Token (`on_new_token`)
- Calls `analyze_opportunity` to check for immediate buy opportunities.
- Initiates async tasks to fetch initial ATH and top holders (and check top holders safety).

### 3. Token Removed (`on_token_removed`)
- If the token is currently being traded, it immediately executes a **SELL** with reason `TOKEN_REMOVED`.
- Attempts to fetch the last transaction price to update the final market cap before selling.

### 4. Trade Execution (`execute_trade`)
- **BUY:**
    - Verifies token is not already traded.
    - Records entry price (Market Cap in USD) and time.
    - Deducts position size + calculated fees from balance.
- **SELL:**
    - Verifies token is currently traded.
    - Calculates profit based on Market Cap change ratio.
    - Adds (Position Size * Profit Ratio) - Fees to balance.
    - Logs trade result (Profit/Loss, Fees, Reason, Time).
    - Clears active trade state.

## Default Pulse Filters

These defaults are applied when subscribing to the Pulse token feed.

### newPairs (NOT TRACKED FOR NOW)
- **Age:** 2-1 minutes
- **Dev Holding:** Max 20%
- **Holders:** Min 1
- **Insiders:** Max 30%
- **Market Cap:** Max $20,000
- **Volume:** Min $200
- **Protocols:** bags, bonk, boop, pump

### finalStretch
- **Age:** Max 20 minutes
- **Market Cap:** Min $6,000
- **Volume:** Min $4,000
- **Protocols:** bags, bonk, boop, pump

### migrated (NOT TRACKED FOR NOW)
- **Age:** 65-60 minutes
- **Dev Holding:** Max 20%
- **Fees:** Min 5 SOL
- **Market Cap:** Min $30,000
- **Protocols:** bags, bonk, boop, pump
