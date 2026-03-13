import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetWeatherMixin:
    """Mixin for polling and logging macro market weather analytics (solana ecosystem)."""

    async def _market_weather_loop(self):
        """Background loop querying stealth API every hour for macro context."""
        logger.info("🌤️ Starting Market Weather Background Loop...")
        while True:
            try:
                # Need to wait until StealthBrowser client is attached by feed
                if getattr(self, "client", None) is None:
                    await asyncio.sleep(5)
                    logger.warning("Client not attached yet, retrying market weather fetching...")
                    continue
                    
                logger.debug("Fetching hourly Market Lighthouse data...")
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, self.client.get_market_lighthouse)
                
                if response:
                    pump_data = response.get('1h', {}).get('All')
                    if pump_data:
                        self._analyze_market_weather(pump_data)
                    else:
                        logger.warning("Market Lighthouse response missing '1h.All' data")
                
                # Sleep exactly 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"⚠️ Error in Market Weather Loop: {e}")
                await asyncio.sleep(60) # retry in 1 minute on crash

    def _analyze_market_weather(self, pump_data: dict):
        """Prepare Market Lighthouse '1h' -> 'All' data for the SQLite DB."""
        analyzed_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'totalTransactions': int(pump_data.get('totalTransactions', 0)),
            'totalBuyTransactions': int(pump_data.get('totalBuyTransactions', 0)),
            'totalSellTransactions': int(pump_data.get('totalSellTransactions', 0)),
            'totalMigrations': int(pump_data.get('totalMigrations', 0)),
            'totalTokensCreated': int(pump_data.get('totalTokensCreated', 0)),
            'totalTraders': int(pump_data.get('totalTraders', 0)),
            'totalVolume': float(pump_data.get('totalVolume', 0.0)),
            'totalBuyVolume': float(pump_data.get('totalBuyVolume', 0.0)),
            'totalSellVolume': float(pump_data.get('totalSellVolume', 0.0))
        }
        if hasattr(self, "recorder"):
            self.recorder.log_market_weather(analyzed_data)
        logger.info("🌤️ Market Weather logged successfully.")
