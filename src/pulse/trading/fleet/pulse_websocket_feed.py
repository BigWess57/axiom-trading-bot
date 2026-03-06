import asyncio
import logging

from playwright_stealth_browser.provider import BrowserPulseProvider
from playwright_stealth_browser.api_client import StealthApiClient

from src.pulse.tracker import PulseTracker
from src.pulse.trading.fleet.shadow_fleet_manager import ShadowFleetManager
from src.utils.async_utils import bridge_callback

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PulseFeed")

class PulseWebsocketFeed:
    """
    Main entry point for the Shadow Fleet.
    - Connects to Pulse & SOL Price WebSockets.
    - Feeds data to PulseTracker.
    - Orchestrates the ShadowFleetManager.
    """
    
    def __init__(self):
        self.tracker = PulseTracker()
        self.manager = ShadowFleetManager(self.tracker)
        
        # Link Tracker -> Manager
        # Tracker filters/decodes -> Manager enriches -> Fleet executes
        self.tracker.on_update = bridge_callback(self.manager.on_token_update)
        self.tracker.on_new_token = bridge_callback(self.manager.on_new_token)
        self.tracker.on_token_removed = bridge_callback(self.manager.on_token_removed)

    async def on_sol_price_update(self, price: float):
        """Pass SOL price updates to the manager"""
        self.manager.update_sol_price(price)



    async def run(self):
        """Main Life Cycle"""
        logger.info("🚀 Starting Pulse Websocket Feed...")
        
        # Initialize Manager/Fleet
        await self.manager.initialize()

        provider = BrowserPulseProvider()
        try:
            provider.start()
        except RuntimeError as e:
            logger.critical("❌ Browser feed failed to start: %s", e)
            await self.manager.shutdown()
            return

        # Poll until the background thread sets up the Playwright page
        while provider.page is None:
            await asyncio.sleep(0.5)
            
        # The provider creates the stealth browser tab. We wrap it in our StealthApiClient
        # and give it to closed-loop manager to fire JS fetches via the thread
        self.manager.client = StealthApiClient(provider)

        consume_task = asyncio.create_task(
            provider.consume(
                pulse_cb=self.tracker.process_message,
                sol_price_cb=self.on_sol_price_update
            )
        )
        logger.warning("Browser feed started — waiting for Pulse data...")

        runtime_seconds = 1800 # 30 minutes
        logger.warning(f"⏰ Bot scheduled to run for {runtime_seconds/60:.1f} minutes.")
        
        try:
            await asyncio.wait_for(consume_task, timeout=runtime_seconds)
        except asyncio.TimeoutError:
            logger.warning(f"⌛ Validated run duration of {runtime_seconds/60:.1f} minutes completed. Triggering clean shutdown.")
        except asyncio.CancelledError:
            pass  # Normal shutdown — task was cancelled by stop()
        finally:
            logger.warning("Shutting down the shadow fleet...")
            provider.stop()
            consume_task.cancel()
            await self.manager.shutdown()
