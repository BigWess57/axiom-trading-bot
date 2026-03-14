import asyncio
import logging
from typing import Optional
from src.pulse.types import PulseToken, SharedTokenState

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetDataMixin:
    """Mixin for fetching and processing raw JS token and chart data."""

    async def get_latest_market_cap(self, pair_address: str, token_supply: float) -> Optional[float]:
        """
        Fetch the latest market cap for a token.
        """ 
        try:
            logger.debug(f"📉 Rug/Removal detected for {pair_address}. Fetching latest price...")
            loop = asyncio.get_running_loop()
            last_tx = await loop.run_in_executor(None, self.client.get_last_transaction, pair_address)
            
            if last_tx and 'priceSol' in last_tx:
                latest_price_sol = float(last_tx['priceSol'])
                if latest_price_sol > 0:
                    latest_market_cap_usd = latest_price_sol * token_supply * self.current_sol_price
                    logger.debug(f"Updated Market Cap to ${latest_market_cap_usd:.2f} USD based on latest tx price: {latest_price_sol:.10f} SOL")
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

    async def _fetch_holder_data(self, token: PulseToken, state: SharedTokenState):
        """
        Executes a lightweight JS fetch in Chromium to get ONLY top holders.
        Used by the baseline strategy where we don't need historical chart ATH calculations.
        """
        logger.debug("🔍 Fetching JS holder data for %s...", token.ticker)
        loop = asyncio.get_running_loop()
        result = None

        async with self.api_semaphore:
            for attempt in range(1, 4):
                try:
                    result = await loop.run_in_executor(None, self.client.get_holder_data, token.pair_address, False)
                    if result:
                        break
                except Exception as e:
                    if attempt == 3:
                        logger.warning(f"⚠️ Failed to fetch holder data for {token.ticker}: {e}")
                        break
                    await asyncio.sleep(attempt)
        
        if not result:
            logger.warning(f"⚠️ error getting holder data for {token.ticker}")
            self._set_fallback_ath(token, state, "Baseline Fast Import Fallback")
            return
            
        # 1. Process Holders
        if isinstance(result, dict) and result.get('error'):
            logger.warning(f"⚠️ JS Holders error for {token.ticker}: {result.get('error')}")
        else:
            holders = result.get('items', []) if isinstance(result, dict) else result if isinstance(result, list) else []
            if holders and len(holders) > 2:
                state.raw_holders = holders
                logger.debug(f"✅ JS Holders fetched for {token.ticker} (Count: {len(holders)})")
            else:
                logger.warning(f"⚠️ JS Holders empty or invalid for {token.ticker}: {result}")

    def _set_fallback_ath(self, token: PulseToken, state: SharedTokenState, reason: str):
        """Fallback to current MC"""
        logger.warning("WARNING: %s ATH Fallback: %s", token.ticker, reason)
        state.ath_market_cap = token.market_cap * getattr(self, "current_sol_price", 0.0)

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
