import asyncio
import logging
from typing import Dict, List, Any

from src.pulse.tracker import PulseTracker
from src.pulse.types import PulseToken, SharedTokenState
from src.pulse.trading.fleet.virtual_bot import VirtualBot
from src.pulse.trading.fleet.shadow_recorder import ShadowRecorder
from src.pulse.trading.fleet.strategy_randomizer import StrategyRandomizer
from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG
from src.config.baseline_strategy_config import get_baseline_config
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig
from src.pulse.trading.fleet.shadow_fleet_mixins import ShadowFleetHelpersMixin

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetManager(ShadowFleetHelpersMixin):
    """
    The Orchestrator.
    - Owns the shared TokenState (ATH, Snapshots, Holders).
    - Fetches heavy data (Holders, Charts) ONCE per token.
    - Multicasts updates to the Fleet of VirtualBots.
    """
    
    def __init__(self, tracker: PulseTracker, baseline_mode: bool = False):
        self.tracker = tracker
        self.recorder = ShadowRecorder()
        self.baseline_mode = baseline_mode
        
        self.bots: List[VirtualBot] = []
        self.shared_tokens: Dict[str, SharedTokenState] = {} # Shared State
        
        self.current_sol_price = 0.0

        self.client: Any = None
        self.api_semaphore = asyncio.Semaphore(1)

    async def initialize(self):
        """Initialize resources and fleet"""
        logger.info("Initializing Shadow Fleet Manager...")
        self._spawn_fleet()
        logger.info(f"Fleet Ready: {len(self.bots)} bots active.")
        
        # Launch Market Weather polling loop
        asyncio.create_task(self._market_weather_loop())

    async def shutdown(self):
        """Shutdown resources and fleet"""
        logger.info("Shadow Fleet Manager shutting down...")
        for bot in self.bots:
            bot.shutdown(self.shared_tokens)

    def _spawn_fleet(self):
        """Create the swarm of virtual bots"""
        if self.baseline_mode:
            logger.info("Spawning baseline fleet in isolated mode...")
            self._add_bot("BASELINE_BOT_1", get_baseline_config(), strategy_type="baseline")
        else:
            # Always add the base strategy for comparison
            self._add_bot("BASE", DEFAULT_STRATEGY_CONFIG, strategy_type="core")
            
        # Determine how many random bots to spawn
        num_random_bots = 500
        logger.info(f"Generating {num_random_bots} randomized strategies...")
        
        # Generate configs
        randomized_configs: Dict[str, Dict[str, Any]] = StrategyRandomizer.generate_randomized_configs(num_random_bots, strategy_type="baseline" if self.baseline_mode else "core")
        
        # Add them to the fleet
        for bot_name, conf in randomized_configs.items():
            if self.baseline_mode:
                self._add_bot(bot_name, conf, strategy_type="baseline")
            else:
                self._add_bot(bot_name, conf, strategy_type="core")

    def _add_bot(self, name: str, config_dict: Dict[str, Any], strategy_type: str = "core"):
        """Add a bot to the fleet"""
        if strategy_type == "baseline":
            strategy_config = BaselineStrategyConfig(config_dict)
        else:
            strategy_config = StrategyConfig(config_dict)
        bot = VirtualBot(name, strategy_config, self.recorder, strategy_type=strategy_type)
        self.bots.append(bot)

    def update_sol_price(self, price: float):
        """Update SOL price"""
        self.current_sol_price = price

    # ------------------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------------------

    async def on_token_update(self, token: PulseToken):
        """Multicast Update"""
        logger.debug(f"Processing update for token: {token.ticker}")
        
        # 1. Manage Shared State
        if token.pair_address not in self.shared_tokens:
            self.shared_tokens[token.pair_address] = SharedTokenState(token=token)
            
        state = self.shared_tokens[token.pair_address]
        
        # Fallback trigger if 'update' arrived before 'new_token'
        if not state.is_fetching_data:
            state.is_fetching_data = True
            asyncio.create_task(self._process_new_token_workflow(token, state))
            
        # Wait safely for the JS Chromium payload to finish gathering holders/chart if still initializing
        await state.init_event.wait()
        
        state.token = token # Update latest data
        
        # 2. Enhance State (Snapshot, ATH)
        # Record internal array snapshot
        self._record_snapshot(token, state)
        
        # Record to SQLite Database
        self._record_db_snapshot(token, state)
        
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
            # Log exact immutable token data to DB exactly once upon discovery
            self.recorder.log_token(token)
            
        state = self.shared_tokens[token.pair_address]
        
        # Sequentially fetch data (Async to avoid blocking WS loop, but we must AWAIT inside the task)
        # We spawn a background task for the whole workflow so we don't block the WebSocket listener
        if not state.is_fetching_data:
            state.is_fetching_data = True
            asyncio.create_task(self._process_new_token_workflow(token, state))

    async def _process_new_token_workflow(self, token: PulseToken, state: SharedTokenState):
        """
        Background workflow:
        1. Fetch JS Full Analysis (Chart & Holders concurrently in V8)
        2. Call bot.process_new_token
        """
        if self.client:
            if self.baseline_mode:
                await self._fetch_holder_data(token, state)
                # No need to set fallback ATH here since we are not using it in the baseline strategy
            else:
                await self._fetch_full_token_data(token, state)
        
        # Ensure an initial DB snapshot exists *before* bots potentially buy it
        self._record_db_snapshot(token, state)
        
        # Now that state is populated, notify bots
        for bot in self.bots:
            try:
                # We pass the shared state
                # (which now has raw_holders and ath_market_cap populated)
                bot.process_new_token(state)
            except Exception as e:
                logger.error(f"Error in Bot {bot.strategy_id} process_new_token: {e}")
                
        # Mark as officially initialized to unblock queued on_token_update events for this token
        state.init_event.set()

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
            bot.process_token_removed(pair_address, category, latest_market_cap_usd, token_state)
        # Remove token from state
        del self.shared_tokens[pair_address]
