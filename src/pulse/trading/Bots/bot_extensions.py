import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

from src.pulse.types import (
    PulseToken, 
    TokenState, 
    TokenSnapshot, 
    TradeTakenInformation
)

if TYPE_CHECKING:
    from src.pulse.trading.Bots.my_first_bot import ExampleTradingBot

logger = logging.getLogger(__name__)

class BotExtensionsMixin:
    """
    Mixin class containing helper and analysis methods for the trading bot.
    Expects to be mixed into a class that has:
    - self.config (dict) - General bot config
    - self.strategy (Strategy) - Strategy instance with .config attribute
    - self.current_sol_price (float)
    - self.api_semaphore (asyncio.Semaphore)
    - self.client (AxiomTradeApiClient)
    """

    def calculate_fees(self, amount: float) -> float:
        """Calculate fees based on percentage."""
        return amount * self.config['fees_percentage']

    def _format_active_trade(self, info: TradeTakenInformation) -> dict:
        """Format active trade for dashboard."""
        current_mc = info.token.market_cap * self.current_sol_price
        entry_mc = info.buy_market_cap
        
        # Avoid division by zero
        if entry_mc > 0:
            pos_size = info.position_size if info.position_size > 0 else self.config['max_position_size']
            pnl_pct = ((current_mc - entry_mc) / entry_mc * 100)
            pnl_absolute = (pos_size * (current_mc / entry_mc)) - pos_size
        else:
            pnl_pct = 0
            pnl_absolute = 0

        return {
            "token": asdict(info.token),
            "entry_mc": entry_mc,
            "pnl_pct": pnl_pct,
            "pnl_absolute": pnl_absolute,
            "time_bought": info.time_bought.isoformat()
        }

    async def _get_top_holders(self, token: PulseToken):
        """
        Get top holders for a token, and call _check_holder_safety
        Updates state.holder_safety_score.
        """
        state = self.tokens.get(token.pair_address)
        if not state:
            return

        try:
            logger.debug("🔍 Checking holders for %s...", token.ticker)
            loop = asyncio.get_running_loop()
            
            holders = None

            # Fetch holder data (blocking call) - Rate limited via Semaphore + Retry for 500s
            async with self.api_semaphore:
                for attempt in range(1, 4):
                    try:
                        holders = await loop.run_in_executor(None, self.client.get_holder_data, token.pair_address)
                        break
                    except Exception as e:
                        if attempt == 3:
                            logger.warning(f"⚠️ Failed to fetch holder data for {token.ticker} after 3 attempts: {e}")
                            break
                        
                        wait_time = 2 * attempt
                        logger.debug(f"⏳ Retry {attempt}/3 fetching holders for {token.ticker} in {wait_time}s...")
                        await asyncio.sleep(wait_time)
            
            if not holders or len(holders) < 2:
                logger.warning(f"⚠️ Not enough holder data for {token.ticker}")
                state.holder_safety_score = 0.2
                return

            self.strategy.check_holder_safety(state, holders)

        except Exception as e:
            logger.error(f"⚠️ Error checking holders for {token.ticker}: {e}")
            state.holder_safety_score = 0.2

    def _record_snapshot(self, token: PulseToken, state: TokenState):
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
            holders=token.holders
        )

        # Limit history (3 minutes @ 2s = 90 snapshots)
        if len(state.snapshots) > 100: # generous buffer
            state.snapshots.pop(0)

        state.snapshots.append(snapshot)
        logger.debug(f"Recorded snapshot for {token.ticker}: {snapshot}")

    async def _fetch_initial_ath(self, token: PulseToken, state: TokenState):
        """Fetch historical data to set initial ATH"""
        try:
            logger.debug("Fetching initial ATH for %s", token.ticker)
            loop = asyncio.get_running_loop()
            
            # Retry mechanism for metadata (3 attempts)
            pair_info = None
            last_tx_data = None
            
            async with self.api_semaphore:
                for attempt in range(1, 4):
                    try:
                        # Fetch metadata needed for chart request (Pair Info & Last Tx)
                        pair_info = await loop.run_in_executor(None, self.client.get_pair_info, token.pair_address)
                        last_tx_data = await loop.run_in_executor(None, self.client.get_last_transaction, token.pair_address)
                        break # Success
                    except Exception as e:
                        if attempt == 3:
                            logger.warning(f"⚠️ Failed to fetch metadata for {token.ticker} after 3 attempts: {e}")
                            raise e # Re-raise to trigger fallback
                        
                        # Wait before retry (exponential backoff: 2s, 4s)
                        wait_time = 2 * attempt
                        logger.debug(f"⏳ Retry {attempt}/3 fetching metadata for {token.ticker} in {wait_time}s...")
                        await asyncio.sleep(wait_time)
            
            if not pair_info or not last_tx_data:
                raise Exception("Failed to retrieve pair info or last tx")

            # Helper to parse times
            def to_ms(val):
                if isinstance(val, int): return val
                if isinstance(val, str):
                    try:
                        # Parse ISO string
                        dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                        return int(dt.timestamp() * 1000)
                    except:
                        return None
                return None

            open_trading = to_ms(pair_info.get("openTrading"))
            pair_created_at = to_ms(pair_info.get("createdAt"))
            last_tx_time = to_ms(last_tx_data.get("createdAt"))
            
            v = last_tx_data.get("v") or int(datetime.now(timezone.utc).timestamp() * 1000)
            
            # 2. Calculate timestamps for 'from' and 'to' (Last 1 hour)
            to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            from_ts = to_ts - (60 * 60 * 1000) # 1 hour ago
            
            # 3. Fetch candles with correct metadata
            candles_data = await loop.run_in_executor(
                None,
                lambda: self.client.get_pair_chart(
                    pair_address=token.pair_address,
                    from_ts=from_ts,
                    to_ts=to_ts,
                    open_trading=open_trading,
                    pair_created_at=pair_created_at,
                    last_transaction_time=last_tx_time,
                    currency="USD",
                    interval="1m",
                    count_bars=30,
                    v=v
                )
            )
            
            if candles_data:
                # Helper to extract candles list
                candles_list = []
                if isinstance(candles_data, dict):
                    candles_list = candles_data.get('candles') or candles_data.get('bars') or []
                elif isinstance(candles_data, list):
                    candles_list = candles_data
            
                max_high = 0.0
                for candle in candles_list:
                    # Candle format is [timestamp, open, high, low, close, volume]
                    # Index 2 is High
                    high = 0.0
                    if isinstance(candle, list) and len(candle) >= 3:
                         high = float(candle[2])
                    elif isinstance(candle, dict):
                         high = float(candle.get('h', candle.get('high', 0)))
                    
                    if high > max_high:
                        max_high = high
                
                if max_high > 0:
                    # Max High is in USD (default currency for get_pair_chart)
                    # We store ATH in Market Cap (USD).
                    # MC = Price(USD) * Supply.
                    state.ath_market_cap = max_high * token.total_supply
                    logger.debug(f"📈 Fetched & Set Historical ATH for {token.ticker}: ${state.ath_market_cap:.2f}")
                else:
                    logger.debug(f"DEBUG: {token.ticker} max_high was 0. Fallback to current.")
                    state.ath_market_cap = token.market_cap * self.current_sol_price
            else:
                 logger.debug(f"DEBUG: {token.ticker} No candles_data returned.")
                 state.ath_market_cap = token.market_cap * self.current_sol_price

        except Exception as e:
            logger.error(f"⚠️ Error fetching ATH for {token.ticker}: {e}")
            # Fallback
            state.ath_market_cap = token.market_cap * self.current_sol_price
