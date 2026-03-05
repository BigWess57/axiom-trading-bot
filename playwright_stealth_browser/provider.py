"""
BrowserPulseProvider — runs the stealth browser in a background thread
and exposes an async interface for consuming Pulse and SOL price data.

Usage:
    provider = BrowserPulseProvider()
    provider.start()

    async def run():
        await provider.consume(
            pulse_cb=tracker.process_message,
            sol_price_cb=on_sol_price_update,
        )

    asyncio.run(run())
"""
import asyncio
import logging
import threading
import time
import queue
import uuid
from typing import Callable, Awaitable, Any

from .browser import launch_stealth_browser, AUTH_FILE
from .interceptors import attach_interceptors

logger = logging.getLogger(__name__)

# Sentinel to signal the consumer to stop
_STOP = object()


class BrowserPulseProvider:
    """
    Runs a stealth browser in a background thread, intercepts WebSocket
    messages from Pulse and SOL price feeds, and delivers them to async
    callbacks via an asyncio.Queue.

    Raises RuntimeError on start() if auth is missing or browser fails.
    """

    def __init__(self, auth_file: str = AUTH_FILE):
        self._auth_file = auth_file
        self._queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        
        # Thread-safe JS Execution Queue
        self._js_eval_queue: queue.Queue = queue.Queue()
        self._js_results = {}

        # Browser handles — kept for cleanup
        self._sb = None
        self._playwright = None
        self._browser = None
        self.page = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Launch the stealth browser in a background thread.

        Must be called from within a running asyncio event loop (e.g. inside
        an async lifespan or after asyncio.get_event_loop()).

        Raises:
            RuntimeError: if auth file is missing or browser fails to launch.
        """
        self._loop = asyncio.get_event_loop()
        self._queue = asyncio.Queue()
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._browser_thread, daemon=True)
        self._thread.start()
        logger.info("BrowserPulseProvider started (background thread)")
        
    def evaluate_js(self, js_code: str, timeout: float = 60.0) -> Any:
        """
        Thread-safe method to evaluate JS strictly on the browser's background thread.
        Blocks the calling thread until the browser thread executes the JS and returns the result.
        """
        req_id = str(uuid.uuid4())
        self._js_eval_queue.put((req_id, js_code))
        
        start = time.time()
        while time.time() - start < timeout:
            if req_id in self._js_results:
                return self._js_results.pop(req_id)
            time.sleep(0.01) # fast poll
            
        raise TimeoutError(f"evaluate_js timed out after {timeout} seconds")

    def stop(self) -> None:
        """Signal the browser thread to stop and wait for it to finish."""
        logger.info("Stopping BrowserPulseProvider...")
        self._stop_event.set()

        # Unblock the consumer
        if self._queue and self._loop:
            asyncio.run_coroutine_threadsafe(self._queue.put(_STOP), self._loop)

        if self._thread:
            self._thread.join(timeout=10)

        logger.info("BrowserPulseProvider stopped")

    async def consume(
        self,
        pulse_cb: Callable[..., Awaitable[None]],
        sol_price_cb: Callable[[float], Awaitable[None]],
    ) -> None:
        """
        Async generator loop — reads from the queue and dispatches to callbacks.

        Runs until stop() is called or the queue receives the stop sentinel.

        Args:
            pulse_cb: async callable receiving decoded msgpack data (list/tuple)
            sol_price_cb: async callable receiving a SOL price float
        """
        if self._queue is None:
            raise RuntimeError("Call start() before consume()")

        last_warning_time = 0

        while True:
            item = await self._queue.get()
            
            # Monitor the true load of the process instead of the queue
            # Since bridge_callback offloads instantly, the queue is always 0.
            # But the event loop might have thousands of pending tasks.
            active_tasks = len(asyncio.all_tasks())
            if active_tasks > 100:
                now = time.time()
                if now - last_warning_time > 5:  # Warn at most every 5 seconds
                    logger.warning(f"⚠️ HIGH LOAD: {active_tasks} simultaneous asyncio tasks active! Event loop may be overwhelmed.")
                    last_warning_time = now

            if item is _STOP:
                logger.info("Consumer received stop signal")
                break

            kind, data = item

            try:
                if kind == "pulse":
                    await pulse_cb(data)
                elif kind == "sol_price":
                    await sol_price_cb(data)
            except Exception as e:
                logger.error("Error in %s callback: %s", kind, e)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _browser_thread(self) -> None:
        """
        Runs in a background thread.
        Launches the browser, attaches interceptors, then keeps the page
        alive (via Playwright's wait_for_timeout loop) until stop() is called.
        """
        try:
            self._sb, self._playwright, self._browser, page = launch_stealth_browser(
                auth_file=self._auth_file,
                # CRITICAL: attach interceptors before page.goto() so no
                # WebSocket connections opened during page load are missed.
                pre_navigate=lambda p: attach_interceptors(p, self._queue, self._loop),
            )
            self.page = page
        except RuntimeError as e:
            logger.error("BrowserPulseProvider failed to start: %s", e)
            # Signal consumer to stop so the server doesn't hang
            if self._queue and self._loop:
                asyncio.run_coroutine_threadsafe(self._queue.put(_STOP), self._loop)
            raise

        logger.info("Browser ready — intercepting WebSocket feeds")

        # Keep the page alive in 50ms ticks until stop() is signalled
        ticks = 0
        while not self._stop_event.is_set():
            try:
                # Process any pending Javascript execution requests from other threads
                while not self._js_eval_queue.empty():
                    req_id, js_code = self._js_eval_queue.get_nowait()
                    try:
                        res = page.evaluate(js_code)
                        self._js_results[req_id] = res
                    except Exception as e:
                        logger.error(f"JS Eval Error in browser thread: {e}")
                        self._js_results[req_id] = {"error": str(e)}
                        
                page.wait_for_timeout(50)
                ticks += 1
                
                # Periodically harvest fresh auth cookies (every 5 minutes / 300s -> 6000 ticks)
                # The browser natively refreshes its own session, bypassing Cloudflare 418 completely.
                if ticks % 6000 == 0 and self._queue and self._loop:
                    try:
                        cookies = page.context.cookies()
                        auth_cookies = {c['name']: c['value'] for c in cookies if c['name'] in ('auth-access-token', 'auth-refresh-token')}
                        
                        if auth_cookies:
                            asyncio.run_coroutine_threadsafe(
                                self._queue.put(("auth_refresh", auth_cookies)),
                                self._loop
                            )
                        else:
                            logger.warning("⚠️ No auth cookies found in stealth browser context.")
                    except Exception as e:
                        logger.error("❌ Failed to extract cookies from Playwright context: %s", e)

            except Exception:
                # Page closed or browser crashed
                logger.warning("Browser page no longer responsive — stopping")
                break

        # Cleanup
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug("Cleanup error (non-fatal): %s", e)
