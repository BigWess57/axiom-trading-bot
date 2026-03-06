import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from src.pulse.types import PulseToken, SharedTokenState, TokenSnapshot

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetHelpersMixin:
    """Mixin containing helper methods for ShadowFleetManager."""

    async def get_latest_market_cap(self, pair_address: str, token_supply: float) -> Optional[float]:
        """
        Fetch the latest market cap for a token.
        """ 
        # Attempt to get the latest transaction to update the price before selling
        try:
            logger.info(f"📉 Rug/Removal detected for {pair_address}. Fetching latest price...")
            loop = asyncio.get_running_loop()
            last_tx = await loop.run_in_executor(None, self.client.get_last_transaction, pair_address)
            
            if last_tx and 'priceSol' in last_tx:
                latest_price_sol = float(last_tx['priceSol'])
                if latest_price_sol > 0:
                    latest_market_cap_usd = latest_price_sol * token_supply * self.current_sol_price
                    logger.info(f"Updated Market Cap to ${latest_market_cap_usd:.2f} USD based on latest tx price: {latest_price_sol:.10f} SOL")
                    return latest_market_cap_usd

        except Exception as e:
            logger.error(f"⚠️ Failed to fetch last transaction for {pair_address}: {e}")
            return None


    async def _fetch_full_token_data(self, token: PulseToken, state: SharedTokenState):
        """
        Executes a native JS Promise.all payload in Chromium to fetch
        historical chart data and top holders concurrently.
        """
        logger.debug("🔍 Fetching full JS token analysis for %s...", token.ticker)
        loop = asyncio.get_running_loop()
        result = None

        # Using a python semaphore here to control evaluation rate slightly if desired
        async with self.api_semaphore:
            for attempt in range(1, 4):
                try:
                    result = await loop.run_in_executor(None, self.client.get_full_token_analysis, token.pair_address)
                    if result:
                        break
                except Exception as e:
                    if attempt == 3:
                        logger.warning(f"⚠️ Failed to fetch full analysis for {token.ticker}: {e}")
                        break
                    await asyncio.sleep(attempt)
        
        if not result:
            logger.warning(f"⚠️ error getting full token analysis for {token.ticker}")
            self._set_fallback_ath(token, state, "Error JS Fetch")
            return

        # 1. Process Holders
        holder_data = result.get('holder_data')
        if holder_data is not None:
            if isinstance(holder_data, dict) and holder_data.get('error'):
                logger.warning(f"⚠️ JS Holders error for {token.ticker}: {holder_data.get('error')}")
            else:
                holders = holder_data.get('items', []) if isinstance(holder_data, dict) else holder_data
                if holders and len(holders) > 2:
                    state.raw_holders = holders
                    logger.debug(f"✅ JS Holders fetched for {token.ticker} (Count: {len(holders)})")
                else:
                    logger.warning(f"⚠️ JS Holders empty or invalid for {token.ticker}: {holder_data}")

        # 2. Process ATH from Chart
        chart_data = result.get('chart_data')
        if chart_data and not (isinstance(chart_data, dict) and chart_data.get('error')):
            ath = self._extract_ath_from_candles(chart_data)
            if ath > 0:
                state.ath_market_cap = ath * token.total_supply
                logger.debug("📈 JS Fetched & Set Historical ATH for %s: $%.2f", token.ticker, state.ath_market_cap)
            else:
                self._set_fallback_ath(token, state, "Max high 0")
        else:
            self._set_fallback_ath(token, state, "Chart error")

    def _set_fallback_ath(self, token: PulseToken, state: SharedTokenState, reason: str):
        """Fallback to current MC"""
        logger.warning("WARNING: %s ATH Fallback: %s", token.ticker, reason)
        state.ath_market_cap = token.market_cap * self.current_sol_price

    def _extract_ath_from_candles(self, candles_data) -> float:
        if not candles_data:
            return 0.0
            
        candles_list = []
        if isinstance(candles_data, dict):
            candles_list = candles_data.get('candles') or candles_data.get('bars') or []
        elif isinstance(candles_data, list):
            candles_list = candles_data

        max_high = 0.0
        for candle in candles_list:
            high = 0.0
            if isinstance(candle, list) and len(candle) >= 3:
                 high = float(candle[2])
            elif isinstance(candle, dict):
                 high = float(candle.get('h', candle.get('high', 0)))
            
            max_high = max(max_high, high)
        return max_high

    def _record_snapshot(self, token: PulseToken, state: SharedTokenState):
        """Record a snapshot of token metrics (every ~2 seconds)"""
        now = datetime.now(timezone.utc)
        
        if state.last_snapshot_time:
            delta = (now - state.last_snapshot_time).total_seconds()
            if delta < 2.0:
                return

        state.last_snapshot_time = now
        
        # Create Snapshot
        snapshot = TokenSnapshot(
            timestamp=now,
            market_cap=token.market_cap * self.current_sol_price,
            txns=token.txns_total,
            buys=token.buys_total,
            sells=token.sells_total,
            holders=token.holders,
            kols=token.famous_kols,
            users_watching=token.active_users_watching
        )

        # Limit history (3 minutes @ 2s = 90 snapshots)
        if len(state.snapshots) > 100: # generous buffer
            state.snapshots.pop(0)

        state.snapshots.append(snapshot)
        logger.debug(f"Recorded snapshot for {token.ticker}: {snapshot}")

    def _record_db_snapshot(self, token: PulseToken, state: SharedTokenState):
        """Record a mutable snapshot to the SQLite database (every ~2 seconds)"""
        now = datetime.now(timezone.utc)
        
        if state.last_db_snapshot_time:
            delta = (now - state.last_db_snapshot_time).total_seconds()
            if delta < 2.0:
                return

        state.last_db_snapshot_time = now
        
        # Log to DB and save the returned primary key ID
        inserted_id = self.recorder.log_db_snapshot(token, now.isoformat())
        if inserted_id:
            state.latest_db_snapshot_id = inserted_id

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
        self.recorder.log_market_weather(analyzed_data)
        logger.info("🌤️ Market Weather logged successfully.")
