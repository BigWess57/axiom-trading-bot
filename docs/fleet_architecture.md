# Shadow Fleet Architecture

## **Overview**
The **Shadow Fleet** is a high-performance, virtual trading simulation engine designed to test trading strategies against live market data in real-time. It mimics "real" trading execution but operates entirely in memory (shadow mode), allowing for risk-free strategy validation and optimization.

## **Directory Structure**
The core logic resides in `src/pulse/trading/fleet/`:

```
src/pulse/trading/fleet/
├── __init__.py               # Exports key classes for external use
├── __main__.py               # Entry point for running the fleet independently
├── pulse_websocket_feed.py   # WebSocket Connection Manager
├── shadow_fleet_manager.py   # Core Orchestrator (The "Brain")
├── virtual_bot.py            # Individual Strategy Executor (The "Worker")
└── shadow_recorder.py        # logging & Analytics (The "Scribe")
```

---

## **Key Components**

### **1. PulseWebsocketFeed (`pulse_websocket_feed.py`)**
*   **Role:** The **Data Ingestor**.
*   **Responsibilities:**
    *   Maintains stable WebSocket connections to the Pulse and Token Price feeds.
    *   Handles connection retries and authentication.
    *   Passes raw messages to the Manager.
*   **Key Concept:** "Dumb pipe" - it doesn't process data, it just ensures the pipe stays open.

### **2. ShadowFleetManager (`shadow_fleet_manager.py`)**
*   **Role:** The **Orchestrator**.
*   **Responsibilities:**
    *   **Token Lifecycle:** Detects new tokens, fetches initial metadata (ATH, Holders), and maintains the `SharedTokenState`.
    *   **Bot Management:** Spawns and manages `VirtualBot` instances.
    *   **Data Distribution:** Broadcasts updates (Price, Market Cap) to all active bots.
    *   **Garbage Collection:** Removes tokens that no longer meet criteria (e.g., "Rugged" or "Die-off").
*   **Key Concept:** centralized state management. It holds the "Truth" about the market.

### **3. VirtualBot (`virtual_bot.py`)**
*   **Role:** The **Strategy Executor**.
*   **Responsibilities:**
    *   **Independence:** Each instance represents a single strategy configuration.
    *   **Decision Making:** Evaluates `should_buy` and `should_sell` signals based on its specific `StrategyConfig`.
    *   **Safety Checks:** independent calculation of safety metrics (e.g., Holder Safety Score).
    *   **Execution:** Simulates Buy/Sell orders and calculates PnL (including fees).
*   **Key Concept:** "Shadow Trading". It tracks its own virtual portfolio (`active_positions`) and `past_trades` independently of other bots.

### **4. ShadowRecorder (`shadow_recorder.py`)**
*   **Role:** The **Logger**.
*   **Responsibilities:**
    *   Persists trade data to CSV/Database.
    *   Records detailed metrics: 
            strategy_id: str
            token_symbol: str
            token_address: str
            entry_price: float
            exit_price: float
            pnl_percent: float
            profit: float
            fees_paid: float
            duration_seconds: float
            exit_reason: str
            entry_confidence: float
            timestamp: str  # ISO format
            token_snapshot_json: str = ""
*   **Key Concept:** Auditable history.

---

## **Data Flow**

1.  **Ingestion:** `PulseWebsocketFeed` receives a raw `msgpack` message (e.g., "New Token" or "Price Update").
2.  **Processing:** `ShadowFleetManager` processes the message:
    *   *New Token:* Fetches historical data (ATH), checks filters, created `SharedTokenState`.
    *   *Update:* Updates the `SharedTokenState` (Price, MC).
3.  **Distribution:** The Manager calls `bot.process_update(state)` on every active `VirtualBot`.
4.  **Reaction:**
    *   `VirtualBot` checks its strategy rules against the new state.
    *   If a signal triggers (Buy/Sell), it executes a "Virtual Trade".
5.  **Recording:** The trade result is sent to `ShadowRecorder` for permanent storage.

## **Execution**
Run the fleet as a standalone module:
```bash
python -m src.pulse.trading.fleet
```
This triggers `__main__.py`, which initializes the Feed and Manager, and starts the event loop.
