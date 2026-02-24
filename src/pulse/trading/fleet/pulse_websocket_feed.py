import asyncio
import logging

from playwright_stealth_browser.provider import BrowserPulseProvider

from src.pulse.tracker import PulseTracker
from src.pulse.trading.fleet.shadow_fleet_manager import ShadowFleetManager
from src.utils.connection_helpers import create_authenticated_client
from src.utils.async_utils import bridge_callback
from src.utils.connection_helpers import save_tokens_to_env

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

    async def on_auth_cookies_received(self, cookies: dict):
        """Pass harvested Playwright cookies down to the AxiomTradeClient to avoid Cloudflare 418 refresh blocks."""
        try:
            if self.manager and self.manager.client and hasattr(self.manager.client, 'auth_manager'):
                auth_token = cookies.get('auth-access-token')
                refresh_token = cookies.get('auth-refresh-token')
                
                if auth_token and refresh_token:
                    logger.info("🍪 Syncing fresh auth cookies from stealth browser to REST client...")
                    self.manager.client.auth_manager._set_tokens(
                        auth_token,
                        refresh_token,
                        expires_in=3600,
                        save_tokens=True
                    )
                    try:
                        save_tokens_to_env(self.manager.client)
                        logger.debug("💾 Sycned browser auth tokens saved to .env file.")
                    except Exception as e:
                        logger.error("❌ Failed to save synced tokens to .env: %s", e)
                else:
                    logger.warning("⚠️ Received auth_refresh event, but cookies were missing token data.")
        except Exception as e:
            logger.error("❌ Error applying synced browser cookies to auth manager: %s", e)

    async def run(self):
        """Main Life Cycle"""
        logger.info("🚀 Starting Pulse Websocket Feed...")
        
        # Initialize Manager/Fleet
        await self.manager.initialize()
        
        self.manager.client = create_authenticated_client()
        if self.manager.client is None:
            logger.error("❌ Failed to create authenticated client.")
            await self.manager.shutdown()
            return

        provider = BrowserPulseProvider()
        try:
            provider.start()
        except RuntimeError as e:
            logger.critical("❌ Browser feed failed to start: %s", e)
            await self.manager.shutdown()
            return

        consume_task = asyncio.create_task(
            provider.consume(
                pulse_cb=self.tracker.process_message,
                sol_price_cb=self.on_sol_price_update,
                auth_cb=self.on_auth_cookies_received,
            )
        )
        logger.warning("Browser feed started — waiting for Pulse data...")

        runtime_seconds = 7200 # 2 hours
        logger.warning(f"⏰ Bot scheduled to run for {runtime_seconds/60/60:.1f} hours.")
        
        try:
            await asyncio.wait_for(consume_task, timeout=runtime_seconds)
        except asyncio.TimeoutError:
            logger.warning(f"⌛ Validated run duration of {runtime_seconds/60/60:.1f} hours completed. Triggering clean shutdown.")
        except asyncio.CancelledError:
            pass  # Normal shutdown — task was cancelled by stop()
        finally:
            logger.warning("Shutting down the shadow fleet...")
            provider.stop()
            consume_task.cancel()
            await self.manager.shutdown()
