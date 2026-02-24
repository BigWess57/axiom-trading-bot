# Browser WebSocket Feed — Architecture

The `playwright_stealth_browser` library solves one problem: Axiom's API blocks direct WebSocket connections with HTTP 418 (bot detection). This library routes all WebSocket data through a real stealth browser, making the traffic indistinguishable from a human user.

## Why a Browser?

Direct `websockets` connections are fingerprinted and blocked by Cloudflare. A real Chrome browser, launched via SeleniumBase with anti-detection patches, passes all bot checks. Playwright then intercepts the WebSocket frames the browser receives — giving us the data without ever opening our own connection.

---

## Module Map

```
playwright_stealth_browser/
├── endpoints.py       # URL constants (HTTP + WebSocket)
├── browser.py         # Launch stealth Chrome, load auth, hook pre-navigation
├── interceptors.py    # Attach WS listeners, decode frames, put onto queue
├── provider.py        # Public interface: start / stop / consume
└── __init__.py        # Exports BrowserPulseProvider
```

---

## How It Works

### Thread Model

The library uses two threads:

```
Main thread (asyncio event loop)
│   FastAPI / bot logic
│   consume() loop reads from queue
│   Dispatches to pulse_cb / sol_price_cb
│
└── Background thread (no event loop)
        SeleniumBase Chrome (headless)
        Playwright CDP connection
        WebSocket frame callbacks fire here
        → asyncio.run_coroutine_threadsafe → queue
```

The browser runs **synchronously** in its own thread. Playwright's WebSocket event callbacks are sync too. But our application is async. The bridge between them is `asyncio.Queue` + `run_coroutine_threadsafe`.

### Data Flow

```
Axiom servers
    │
    │  WebSocket frames (binary msgpack / JSON)
    ▼
Stealth Chrome (SeleniumBase + CDP)
    │
    │  Playwright page.on("websocket")
    ▼
interceptors.py — on_websocket(ws)
    │
    ├── Pulse frame  → msgpack.unpackb() → queue.put(("pulse", data))
    └── SOL frame    → json.loads()      → queue.put(("sol_price", float))
                                                  │
                              asyncio.run_coroutine_threadsafe
                                                  │
                                                  ▼
                                         asyncio.Queue
                                                  │
                                         consume() loop
                                                  │
                              ┌───────────────────┴─────────────────────┐
                              ▼                                         ▼
                      pulse_cb(data)                        sol_price_cb(price)
                  tracker.process_message()              on_sol_price_update()
```

---

## Files in Detail

### `endpoints.py`
Central registry of all URLs. Import from here instead of hardcoding strings.

```python
class Websockets:
    PULSE       = "wss://pulse2.axiom.trade/ws"   # binary msgpack
    MAIN        = "wss://cluster9.axiom.trade/"    # JSON, room-based
    TOKEN_PRICE = "wss://socket8.axiom.trade/"     # (not yet used)
```

---

### `browser.py` — `launch_stealth_browser()`

Responsible for:
1. **Auto-detecting** Playwright's Chromium binary (`~/.cache/ms-playwright/`)
2. **Launching** SeleniumBase CDP Chrome (headless, anti-fingerprint patches)
3. **Connecting** Playwright over the CDP endpoint
4. **Loading auth state** from `.auth/axiom_auth_sb.json` into a new context
5. **Calling `pre_navigate(page)`** before `page.goto()` — critical for interceptor timing
6. **Navigating** to `axiom.trade/pulse`

**Fail-fast**: raises `RuntimeError` if the auth file is missing or the browser crashes. No partial startup.

> **Why `pre_navigate`?**  
> WebSocket connections are opened *during* page load. If interceptors are attached after `goto()`, the initial connections are already missed. The hook lets the provider attach listeners before any navigation happens.

---

### `interceptors.py` — `attach_interceptors()`

Uses factory functions to create handlers bound to a specific `queue` and `loop`:

```python
def make_pulse_handler(queue, loop) -> Callable:
    def on_pulse_frame(payload: bytes):
        decoded = msgpack.unpackb(payload, raw=False)
        asyncio.run_coroutine_threadsafe(queue.put(("pulse", decoded)), loop)
    return on_pulse_frame
```

**Why factories and not plain functions with extra parameters?**  
Playwright's `ws.on("framereceived", handler)` calls the handler with exactly one argument (the frame payload). Factories pre-bind `queue` and `loop` via closure, so the handler signature stays compatible.

`attach_interceptors()` registers a single `page.on("websocket")` listener that routes each new WebSocket to the right handler based on its URL.

---

### `provider.py` — `BrowserPulseProvider`

The public interface. Manages the browser thread lifecycle and exposes three methods:

| Method | Description |
|--------|-------------|
| `start()` | Captures the current event loop, creates the queue, spawns the browser thread. Must be called while an asyncio loop is running. |
| `stop()` | Sets a stop event, puts `_STOP` sentinel on the queue (to unblock `consume()`), joins the thread. |
| `consume(pulse_cb, sol_price_cb)` | Async loop that reads from the queue and dispatches to callbacks. Blocks until `stop()` is called. |

**Sentinel pattern**: `_STOP = object()` is a unique object used to signal the consumer to break its loop. `is _STOP` checks identity, not equality — impossible to mistake for real data.

**Keep-alive loop** inside `_browser_thread`:
```python
while not self._stop_event.is_set():
    page.wait_for_timeout(1000)  # keeps Playwright processing events
```
This is a **blocking** Playwright call. It must run in the background thread — if called on the asyncio event loop, it would freeze the entire server for 1 second per tick.

---

## Authentication

Auth state is saved by running the login script once:

```bash
python playwright_tests/axiom_login_tests.py
```

This stores cookies and local storage to `playwright_tests/.auth/axiom_auth_sb.json`. `launch_stealth_browser()` loads this file into the browser context via `browser.new_context(storage_state=auth_file)`.

---

## Integration Pattern

```python
# Inside asyncio lifespan / async run()
provider = BrowserPulseProvider()

try:
    provider.start()
except RuntimeError as e:
    logger.critical("Browser feed failed to start: %s", e)
    return

consume_task = asyncio.create_task(
    provider.consume(
        pulse_cb=tracker.process_message,
        sol_price_cb=on_sol_price_update,
    )
)

try:
    await consume_task          # blocks here for the lifetime of the feed
except asyncio.CancelledError:
    pass                        # normal shutdown
finally:
    provider.stop()
    consume_task.cancel()
```

Currently used in:
- `src/pulse_dashboard/server/api_with_browser_feed.py` — FastAPI dashboard server
- `src/pulse/trading/fleet/pulse_websocket_feed.py` — bot trading fleet
