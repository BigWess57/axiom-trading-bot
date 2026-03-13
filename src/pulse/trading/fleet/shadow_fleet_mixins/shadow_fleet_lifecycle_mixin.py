import asyncio
import logging
import random
import statistics
import json
import os
from datetime import datetime
from typing import Dict, Any

from src.pulse.trading.fleet.virtual_bot import VirtualBot
from src.pulse.trading.fleet.strategy_randomizer import StrategyRandomizer
from src.config.default_strategy import DEFAULT_STRATEGY_CONFIG
from src.config.baseline_strategy_config import get_baseline_config
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig
from src.pulse.trading.fleet.genetic_optimizer import GeneticOptimizer

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetLifecycleMixin:
    """Mixin for handling bot spawning, adding bots, and evolutionary loops."""
    # Type hints and default values for the linter to know these are defined on the manager subclass
    current_generation: int = 0
    max_bots: int = 500
    bots: list = None
    bot_index_map: dict = None

    def _spawn_fleet(self):
        """Create the swarm of virtual bots"""
        initial_configs = {}
        
        base_name = "G000_Bot_000_BASE"
        if getattr(self, "baseline_mode", False):
            logger.info("Spawning baseline fleet in isolated mode...")
            self._add_bot(0, base_name, get_baseline_config(), strategy_type="baseline")
            initial_configs[base_name] = get_baseline_config()
        else:
            # Always add the base strategy for comparison
            self._add_bot(0, base_name, DEFAULT_STRATEGY_CONFIG, strategy_type="core")
            initial_configs[base_name] = DEFAULT_STRATEGY_CONFIG
            
        logger.info(f"Generating {self.max_bots - 1} randomized strategies...")
        
        # Generate configs
        randomized_configs: Dict[str, Dict[str, Any]] = StrategyRandomizer.generate_randomized_configs(
            self.max_bots - 1, strategy_type="baseline" if getattr(self, "baseline_mode", False) else "core"
        )
        
        # Add them to the fleet
        idx = 1
        for _, conf in randomized_configs.items():
            bot_name = f"G000_Bot_{idx:03d}"
            if getattr(self, "baseline_mode", False):
                self._add_bot(idx, bot_name, conf, strategy_type="baseline")
            else:
                self._add_bot(idx, bot_name, conf, strategy_type="core")
            initial_configs[bot_name] = conf
            idx += 1
            
        if hasattr(self, "master_config_path"):
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
            await asyncio.sleep(getattr(self, "evolution_interval_minutes", 60) * 60)
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
        
        if hasattr(self, "leaderboard_path"):
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
        strategy_type = "baseline" if getattr(self, "baseline_mode", False) else "core"
        
        logger.info(f"⚔️ Culling bottom {len(losers)} bots. Elites selected for breeding: {len(elites)}.")
        logger.info(f"🧬 Spawning {len(elites)} Generation {self.current_generation:02d} children with starting PnL {median_pnl:.4f} SOL...")
        
        freed_indices = []
        for weak_bot in losers:
            freed_indices.append(getattr(weak_bot, "fleet_index", 0))
            weak_bot.is_dead = True
            weak_bot.shutdown(getattr(self, "shared_tokens", {}))
            if weak_bot in getattr(self, "bots", []):
                self.bots.remove(weak_bot)
            if getattr(weak_bot, "fleet_index", 0) in getattr(self, "bot_index_map", {}):
                del self.bot_index_map[weak_bot.fleet_index]
                
        new_configs = {}
        for idx in freed_indices:
            p1 = random.choice(elites)
            p2 = random.choice(elites)
            
            child_conf = GeneticOptimizer.crossover(p1.config.raw_config, p2.config.raw_config)
            child_conf = GeneticOptimizer.mutate(child_conf, mutation_rate=0.3, max_variance=0.1)
            
            bot_name = f"G{self.current_generation:03d}_Bot_{idx:03d}"
            
            self._add_bot(idx, bot_name, child_conf, strategy_type=strategy_type, initial_pnl=median_pnl, virtual_trades_completed=min_trades)
            new_configs[bot_name] = child_conf
            
        if hasattr(self, "master_config_path") and os.path.exists(self.master_config_path):
            with open(self.master_config_path, "r") as f:
                master_data = json.load(f)
            master_data.update(new_configs)
            with open(self.master_config_path, "w") as f:
                json.dump(master_data, f, indent=4)
            
        logger.info(f"✅ Evolution complete! Fleet size: {len(getattr(self, 'bots', []))}")
