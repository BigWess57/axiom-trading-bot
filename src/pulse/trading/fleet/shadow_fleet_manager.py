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

from src.pulse.trading.fleet.genetic_optimizer import GeneticOptimizer
import random
import statistics
from pathlib import Path
from datetime import datetime
import json
import os

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
        
        # Evolution Tracking
        self.evolution_interval_minutes = 60
        self.current_generation = 0
        self.max_bots = 500
        
        # Database / Master Config Tracking
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.master_config_path = Path(f"data/config_logs/fleet_configs_{self.session_timestamp}.json")
        self.leaderboard_path = Path(f"data/config_logs/leaderboard_{self.session_timestamp}.txt")
        self.master_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Map bot index -> virtual bot
        self.bot_index_map: Dict[int, VirtualBot] = {}

    async def initialize(self):
        """Initialize resources and fleet"""
        logger.info("Initializing Shadow Fleet Manager...")
        self._spawn_fleet()
        logger.info(f"Fleet Ready: {len(self.bots)} bots active.")
        
        # Launch Market Weather polling loop
        asyncio.create_task(self._market_weather_loop())
        asyncio.create_task(self._evolution_loop())

    async def shutdown(self):
        """Shutdown resources and fleet"""
        logger.info("Shadow Fleet Manager shutting down...")
        for bot in self.bots:
            bot.shutdown(self.shared_tokens)

    def _spawn_fleet(self):
        """Create the swarm of virtual bots"""
        initial_configs = {}
        
        base_name = "G00_Bot_000_BASE"
        if self.baseline_mode:
            logger.info("Spawning baseline fleet in isolated mode...")
            self._add_bot(0, base_name, get_baseline_config(), strategy_type="baseline")
            initial_configs[base_name] = get_baseline_config()
        else:
            # Always add the base strategy for comparison
            self._add_bot(0, base_name, DEFAULT_STRATEGY_CONFIG, strategy_type="core")
            initial_configs[base_name] = DEFAULT_STRATEGY_CONFIG
            
        logger.info(f"Generating {self.max_bots - 1} randomized strategies...")
        
        # Generate configs
        randomized_configs: Dict[str, Dict[str, Any]] = StrategyRandomizer.generate_randomized_configs(self.max_bots - 1, strategy_type="baseline" if self.baseline_mode else "core")
        
        # Add them to the fleet
        idx = 1
        for _, conf in randomized_configs.items():
            bot_name = f"G00_Bot_{idx:03d}"
            if self.baseline_mode:
                self._add_bot(idx, bot_name, conf, strategy_type="baseline")
            else:
                self._add_bot(idx, bot_name, conf, strategy_type="core")
            initial_configs[bot_name] = conf
            idx += 1
            
        with open(self.master_config_path, "w") as f:
            json.dump(initial_configs, f, indent=4)
        logger.info(f"💾 Initialized Master Config JSON: {self.master_config_path}")

    def _add_bot(self, index: int, name: str, config_dict: Dict[str, Any], strategy_type: str = "core", initial_pnl: float = 0.0, virtual_trades_completed: int = 0):
        """Add a bot to the fleet at a specific index block."""
        if strategy_type == "baseline":
            strategy_config = BaselineStrategyConfig(config_dict)
        else:
            strategy_config = StrategyConfig(config_dict)
        bot = VirtualBot(name, strategy_config, self.recorder, strategy_type=strategy_type)
        bot.fleet_index = index 
        bot.global_state.total_pnl = initial_pnl
        bot.global_state.current_balance = strategy_config.account.starting_balance + initial_pnl
        bot.global_state.total_trades = virtual_trades_completed 
        self.bots.append(bot)
        self.bot_index_map[index] = bot

    async def _evolution_loop(self):
        """Continuously evolves the fleet every N minutes."""
        while True:
            await asyncio.sleep(self.evolution_interval_minutes * 60)
            self._evolve_fleet()
            
    def _evolve_fleet(self):
        """Perform Natural Selection on the fleet and append configs to master file."""
        logger.info(f"🧬 Starting Generation {self.current_generation + 1} Evolution...")
        
        min_trades = 5
        eligible_bots = [b for b in self.bots if b.global_state.total_trades >= min_trades]
        
        if len(eligible_bots) < 10:
            logger.info("Not enough eligible bots to evolve yet.")
            return
            
        eligible_bots.sort(key=lambda b: b.global_state.total_pnl, reverse=True)
        
        all_pnls = [b.global_state.total_pnl for b in eligible_bots]
        median_pnl = statistics.median(all_pnls)
        
        with open(self.leaderboard_path, "a") as f:
            f.write(f"\n======== GENERATION {self.current_generation} END LEADERBOARD ========\n")
            f.write(f"Timestamp: {datetime.now().isoformat()} | Median Fleet PnL: {median_pnl:.2f} SOL\n")
            f.write("--- TOP 10 BOTS ---\n")
            for i, b in enumerate(eligible_bots[:10]):
                f.write(f"{i+1}. {b.strategy_id} | PnL: {b.global_state.total_pnl:+.4f} SOL | Trades: {b.global_state.total_trades} | Win rate: {b.global_state.win_rate:.2f}% | Max Drawdown: {b.global_state.max_drawdown:.2f}%\n")
            f.write("============================================================\n")

        # Keep Top 20% to breed, Kill Bottom 20%
        cull_count = max(2, int(len(eligible_bots) * 0.20))
        elite_count = max(2, int(len(eligible_bots) * 0.20))
        
        elites = eligible_bots[:elite_count]
        losers = eligible_bots[-cull_count:]
        
        self.current_generation += 1
        strategy_type = "baseline" if self.baseline_mode else "core"
        
        logger.info(f"⚔️ Culling bottom {len(losers)} bots. Elites selected for breeding: {len(elites)}.")
        logger.info(f"🧬 Spawning {len(losers)} Generation {self.current_generation:02d} children with starting PnL {median_pnl:.4f} SOL...")
        
        freed_indices = []
        for weak_bot in losers:
            freed_indices.append(getattr(weak_bot, "fleet_index", 0))
            weak_bot.is_dead = True
            weak_bot.shutdown(self.shared_tokens)
            if weak_bot in self.bots:
                self.bots.remove(weak_bot)
            if getattr(weak_bot, "fleet_index", 0) in self.bot_index_map:
                del self.bot_index_map[weak_bot.fleet_index]
                
        new_configs = {}
        for idx in freed_indices:
            p1 = random.choice(elites)
            p2 = random.choice(elites)
            
            child_conf = GeneticOptimizer.crossover(p1.config.raw_config, p2.config.raw_config)
            child_conf = GeneticOptimizer.mutate(child_conf, mutation_rate=0.3, max_variance=0.1)
            
            bot_name = f"G{self.current_generation:02d}_Bot_{idx:03d}"
            
            self._add_bot(idx, bot_name, child_conf, strategy_type=strategy_type, initial_pnl=median_pnl, virtual_trades_completed=min_trades)
            new_configs[bot_name] = child_conf
            
        if os.path.exists(self.master_config_path):
            with open(self.master_config_path, "r") as f:
                master_data = json.load(f)
            master_data.update(new_configs)
            with open(self.master_config_path, "w") as f:
                json.dump(master_data, f, indent=4)
            
        logger.info(f"✅ Evolution complete! Fleet size: {len(self.bots)}")

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
