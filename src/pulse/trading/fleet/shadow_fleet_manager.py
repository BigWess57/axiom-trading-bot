import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from axiomtradeapi.xhr_client import AxiomTradeClient
from src.pulse.tracker import PulseTracker
from src.pulse.types import PulseToken, SharedTokenState, TokenSnapshot
from src.pulse.trading.fleet.virtual_bot import VirtualBot
from src.pulse.trading.fleet.shadow_recorder import ShadowRecorder
from src.pulse.trading.fleet.strategy_randomizer import StrategyRandomizer
from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG
from src.pulse.trading.strategies.strategy_models import StrategyConfig

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetManager:
    """
    The Orchestrator.
    - Owns the shared TokenState (ATH, Snapshots, Holders).
    - Fetches heavy data (Holders, Charts) ONCE per token.
    - Multicasts updates to the Fleet of VirtualBots.
    """
    
    def __init__(self, tracker: PulseTracker):
        self.tracker = tracker
        self.recorder = ShadowRecorder()
        
        self.bots: List[VirtualBot] = []
        self.shared_tokens: Dict[str, SharedTokenState] = {} # Shared State
        
        self.current_sol_price = 0.0

        self.client: AxiomTradeClient = None
        self.api_semaphore = asyncio.Semaphore(4)

    async def initialize(self):
        """Initialize resources and fleet"""
        logger.info("Initializing Shadow Fleet Manager...")
        self._spawn_fleet()
        logger.info(f"Fleet Ready: {len(self.bots)} bots active.")

    async def shutdown(self):
        """Shutdown resources and fleet"""
        logger.info("Shadow Fleet Manager shutting down...")
        for bot in self.bots:
            bot.shutdown()

    def _spawn_fleet(self):
        """Create the swarm of virtual bots"""
        # Always add the base strategy for comparison
        self._add_bot("BASE", DEFAULT_STRATEGY_CONFIG)
        
        # Determine how many random bots to spawn
        num_random_bots = 500
        logger.info(f"Generating {num_random_bots} randomized strategies...")
        
        # Generate configs
        randomized_configs: Dict[str, Dict[str, Any]] = StrategyRandomizer.generate_randomized_configs(num_random_bots)
        
        # Add them to the fleet
        for bot_name, conf in randomized_configs.items():
            self._add_bot(bot_name, conf)

    def _add_bot(self, name: str, config_dict: Dict[str, Any]):
        """Add a bot to the fleet"""
        strategy_config = StrategyConfig(config_dict)
        bot = VirtualBot(name, strategy_config, self.recorder)
        self.bots.append(bot)

    def update_sol_price(self, price: float):
        """Update SOL price"""
        self.current_sol_price = price

    # ------------------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------------------

    async def on_token_update(self, token: PulseToken):
        """Multicast Update"""
        # 1. Manage Shared State
        if token.pair_address not in self.shared_tokens:
            self.shared_tokens[token.pair_address] = SharedTokenState(token=token)
        state = self.shared_tokens[token.pair_address]
        state.token = token # Update latest data
        
        # 2. Enhance State (Snapshot, ATH)
        # Record snapshot
        self._record_snapshot(token, state)
        
        # Check ATH
        current_mc_usd = token.market_cap * self.current_sol_price
        state.ath_market_cap = max(state.ath_market_cap, current_mc_usd)
        
        # 3. Broadcast to Fleet
        for bot in self.bots:
            try:
                bot.process_update(state, self.current_sol_price)
            except Exception as e:
                logger.error(f"Error in Bot {bot.strategy_id}: {e}")

    async def on_new_token(self, token: PulseToken):
        """Handle new token discovery"""
        logger.info(f"🆕 New Token: {token.ticker}")
        
        if token.pair_address not in self.shared_tokens:
            self.shared_tokens[token.pair_address] = SharedTokenState(token=token)
        state = self.shared_tokens[token.pair_address]
        
        # Sequentially fetch data (Async to avoid blocking WS loop, but we must AWAIT inside the task)
        # We spawn a background task for the whole workflow so we don't block the WebSocket listener
        asyncio.create_task(self._process_new_token_workflow(token, state))

    async def _process_new_token_workflow(self, token: PulseToken, state: SharedTokenState):
        """
        Background workflow:
        1. Fetch ATH & Holders (Wait for completion)
        2. Call bot.process_new_token
        """
        if self.client:
            # Run fetches concurrently and wait for BOTH
            await asyncio.gather(
                self._fetch_initial_ath(token, state),
                self._get_top_holders(token)
            )
        
        # Now that state is populated, notify bots
        for bot in self.bots:
            try:
                # We pass the shared state
                # (which now has raw_holders and ath_market_cap populated)
                bot.process_new_token(state)
            except Exception as e:
                logger.error(f"Error in Bot {bot.strategy_id} process_new_token: {e}")

    async def on_token_removed(self, category: str, pair_address: str):
        """Handle token removal"""
        logger.info(f"❌ Token Removed: {pair_address}")
        token_state = self.shared_tokens.get(pair_address)
        if not token_state:
            logger.warning(f"Token {pair_address} not found in shared tokens")
            return
        
        latest_market_cap_usd = await self.get_latest_market_cap(pair_address, token_state.token.total_supply)
        if latest_market_cap_usd is None:
            logger.error(f"Failed to get latest market cap for {pair_address}. Using token_state.token.market_cap (might not be updated)")
            latest_market_cap_usd = token_state.token.market_cap * self.current_sol_price
        for bot in self.bots:
            bot.process_token_removed(pair_address, category, latest_market_cap_usd)
        # Remove token from state
        del self.shared_tokens[pair_address]

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

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

    async def _get_top_holders(self, token: PulseToken):
        """
        Fetch top holders and STORE them in shared state.
        Does NOT check safety (that's the bot's job).
        """
        state = self.shared_tokens.get(token.pair_address)
        if not state:
            return

        try:
            logger.debug("🔍 Fetching holders for %s...", token.ticker)
            loop = asyncio.get_running_loop()
            holders = None

            async with self.api_semaphore:
                for attempt in range(1, 4):
                    try:
                        holders = await loop.run_in_executor(None, self.client.get_holder_data, token.pair_address)
                        break
                    except Exception as e:
                        if attempt == 3:
                            logger.warning(f"⚠️ Failed to fetch holder data: {e}")
                            break
                        await asyncio.sleep(2 * attempt)
            
            if holders and len(holders) > 2:
                # Store RAW holders
                state.raw_holders = holders
                logger.debug(f"✅ Holders fetched for {token.ticker} (Count: {len(holders)})")
                
        except Exception as e:
            logger.error("⚠️ Error in holder fetch: %s", e)

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

    async def _fetch_initial_ath(self, token: PulseToken, state: SharedTokenState):
        """Fetch historical data to set initial ATH"""
        try:
            logger.debug("Fetching initial ATH for %s", token.ticker)
            
            # 1. Fetch Metadata
            pair_info, last_tx_data = await self._fetch_metadata_with_retry(token)
            if not pair_info or not last_tx_data:
                raise RuntimeError("Failed to retrieve pair info or last tx")

            # 2. Calculate Parameters
            params = self._calculate_chart_params(pair_info, last_tx_data)
            
            # 3. Fetch Candles
            candles_data = await self._fetch_candles(token.pair_address, params)
            
            # 4. Determine ATH
            ath = self._extract_ath_from_candles(candles_data)
            
            if ath > 0:
                state.ath_market_cap = ath * token.total_supply
                logger.debug("📈 Fetched & Set Historical ATH for %s: $%.2f", token.ticker, state.ath_market_cap)
            else:
                self._set_feedback_ath(token, state, "Max high 0")

        except Exception as e:
            logger.error("⚠️ Error fetching ATH for %s: %s", token.ticker, e)
            self._set_feedback_ath(token, state, "Error")

    def _set_feedback_ath(self, token: PulseToken, state: SharedTokenState, reason: str):
        """Fallback to current MC"""
        logger.debug("DEBUG: %s ATH Fallback: %s", token.ticker, reason)
        state.ath_market_cap = token.market_cap * self.current_sol_price

    async def _fetch_metadata_with_retry(self, token: PulseToken):
        loop = asyncio.get_running_loop()
        pair_info = None
        last_tx_data = None
        
        async with self.api_semaphore:
            for attempt in range(1, 4):
                try:
                    pair_info = await loop.run_in_executor(None, self.client.get_pair_info, token.pair_address)
                    last_tx_data = await loop.run_in_executor(None, self.client.get_last_transaction, token.pair_address)
                    return pair_info, last_tx_data
                except Exception as e:
                    if attempt == 3:
                        logger.warning("⚠️ Failed to fetch metadata for %s: %s", token.ticker, e)
                        return None, None
                    await asyncio.sleep(2 * attempt)
        return None, None

    def _calculate_chart_params(self, pair_info, last_tx_data):
        def to_ms(val):
            if isinstance(val, int): return val
            if isinstance(val, str):
                try:
                    return int(datetime.fromisoformat(val.replace('Z', '+00:00')).timestamp() * 1000)
                except ValueError:
                    return None
            return None

        to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        return {
            "from_ts": to_ts - (60 * 60 * 1000), # 1 hour ago
            "to_ts": to_ts,
            "open_trading": to_ms(pair_info.get("openTrading")),
            "pair_created_at": to_ms(pair_info.get("createdAt")),
            "last_transaction_time": to_ms(last_tx_data.get("createdAt")),
            "v": last_tx_data.get("v") or to_ts
        }

    async def _fetch_candles(self, pair_address, p):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_pair_chart(
                pair_address=pair_address,
                from_ts=p["from_ts"],
                to_ts=p["to_ts"],
                open_trading=p["open_trading"],
                pair_created_at=p["pair_created_at"],
                last_transaction_time=p["last_transaction_time"],
                currency="USD",
                interval="1m",
                count_bars=30,
                v=p["v"]
            )
        )

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
