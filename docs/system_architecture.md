# Pulse System Architecture

> **Context:** This document outlines the architecture of the `src/pulse` directory, which handles real-time token tracking and automated trading logic capable of reacting to the high-frequency Pulse WebSocket feed.

**Goal:** Provide a robust, modular foundation for high-frequency trading bots that can analyze thousands of token events per second and execute strategies with minimal latency.

## Architecture Overview

- **Data Layer:** `PulseTracker` acts as the source of truth, maintaining the real-time state of all tokens on the network.
- **Trading Layer:** `BaseTradingBot` provides the abstract interface for all bots, handling common utilities like risk checks and Axiom API interaction.
- **Strategy Layer:** Decoupled strategy logic allows defining *rules* separately from the *execution engine*.
- **Data Flow:** Axiom WS -> `PulseDecoder` -> `PulseTracker` -> `TradingBot` (Strategy Evaluation) -> `AxiomTradeClient` (Execution).

---

### [CORE] Component 1: The Data Engine
**Location:** `src/pulse/`

**Files:**
- `decoder.py`: The "Parser".
- `tracker.py`: The "State Machine".
- `types.py`: Centralized type definitions (`PulseToken`, `TokenState`, `TradeResult`, etc.).

**Functionality:**
- **Decoder**: Strictly typed parser that converts raw MessagePack arrays from the WebSocket into rich `PulseToken` objects. Handles versioning and schema changes.
- **Tracker**: The central nervous system. It maintains the in-memory database of every active token. It categorizes tokens (`newPairs`, `finalStretch`, `migrated`) and emits events (`on_update`, `on_new_token`) that downstream bots subscribe to.

### [ABSTRACT] Component 2: Trading Abstraction
**Location:** `src/pulse/trading/base_bot.py`

**Functionality:**
- **Standardization**: Defines the contract that all bots must follow (`analyze_opportunity`, `execute_trade`, `run`).
- **Safety**: Implements shared risk management (Daily Loss Limits, Max Position Size) to prevent catastrophic failures.
- **Utilities**: Wrapper around `AxiomTradeClient` for standardized API access.

### [LOGIC] Component 3: Strategy Definitions
**Location:** `src/pulse/trading/strategies/`

**Files:**
- `core_strategy.py` and `mixins/`: Implements `should_buy`, `should_sell`, and modular confidence scoring logic.
- `strategy_config.py`: Defines configuration dataclasses (`ConfidenceConfig`, `RiskConfig`).

**Functionality:**
- **Pure Logic**: Contains the mathematical specifications or rule sets for trading (e.g., "Buy if Market Cap > $50k AND liquidity > $10k").
- **Reusability**: Strategies are defined as functions or classes that can be plugged into different bots.
- **Dynamic Sizing**: Strategies now return execution directives (e.g., size multipliers based on confidence) rather than just boolean signals.

### [EXECUTION] Component 4: Active Bots
**Location:** `src/pulse/trading/Bots/`

**Files:**
- `my_first_bot.py`: The main trading bot implementation.
- `bot_extensions.py`: A Mixin class (`BotExtensionsMixin`) containing helper methods for analysis, snapshot recording, and PnL formatting.

**Functionality:**
- **The Agents**: These are the runnable classes that instantiate a `PulseTracker`, listen to its events, apply a Strategy, and execute trades.
- **State Management**: Maintains `TokenState` for every tracked token, including `active_trade` information and `past_trades`.
- **Loop**: They run the main event loop, managing the WebSocket connection and orchestrating the life cycle of a trade.

### [VISUALIZATION] Component 5: Dashboard Connector
**Location:** `src/pulse/trading/dashboard_connector.py`

**Functionality:**
- **Bridge**: Pushes internal bot state (active trades, stats) to the local Dashboard API (`src/pulse_dashboard/server/api.py`).
- **Real-time**: Enables the frontend to display live trade updates and PnL.

---

**Current Ecosystem Status:**
- **Data Feed**: Stable and typed (Decoder/Tracker working).
- **Bot Framework**: Abstract base class established.
- **Strategies**: `CoreStrategy` implemented with dynamic position sizing and modular mixin architecture.
- **Visuals**: Web Dashboard integration active.
