import asyncio
import logging
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

from src.pulse.tracker import PulseTracker
from src.pulse.types import SharedTokenState
from src.pulse.trading.fleet.virtual_bot import VirtualBot
from src.pulse.trading.fleet.shadow_recorder import ShadowRecorder

from src.pulse.trading.fleet.shadow_fleet_data_mixin import ShadowFleetDataMixin
from src.pulse.trading.fleet.shadow_fleet_events_mixin import ShadowFleetEventsMixin
from src.pulse.trading.fleet.shadow_fleet_lifecycle_mixin import ShadowFleetLifecycleMixin
from src.pulse.trading.fleet.shadow_fleet_recording_mixin import ShadowFleetRecordingMixin
from src.pulse.trading.fleet.shadow_fleet_weather_mixin import ShadowFleetWeatherMixin

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetManager(
    ShadowFleetDataMixin,
    ShadowFleetEventsMixin,
    ShadowFleetLifecycleMixin,
    ShadowFleetRecordingMixin,
    ShadowFleetWeatherMixin
):
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
        
        # Launch loops
        asyncio.create_task(self._market_weather_loop())
        asyncio.create_task(self._evolution_loop())

    async def shutdown(self):
        """Shutdown resources and fleet"""
        logger.info("Shadow Fleet Manager shutting down...")
        for bot in self.bots:
            bot.shutdown(self.shared_tokens)
