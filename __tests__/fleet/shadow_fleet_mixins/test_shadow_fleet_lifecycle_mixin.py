import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
import statistics

from src.pulse.trading.fleet.shadow_fleet_mixins.shadow_fleet_lifecycle_mixin import ShadowFleetLifecycleMixin
from src.pulse.trading.strategies.strategy_models import StrategyConfig

class DummyManager(ShadowFleetLifecycleMixin):
    def __init__(self):
        self.current_generation = 0
        self.max_bots = 10
        self.bots = []
        self.bot_index_map = {}
        self.recorder = MagicMock()
        self.baseline_mode = False
        self.shared_tokens = {}
        self.leaderboard_path = "dummy_leaderboard.txt"
        self.master_config_path = "dummy_master.json"

@pytest.fixture
def manager():
    return DummyManager()

@patch("src.pulse.trading.fleet.shadow_fleet_mixins.shadow_fleet_lifecycle_mixin.StrategyRandomizer")
def test_spawn_fleet(mock_randomizer, manager):
    # Mock generation of random configs
    mock_randomizer.generate_randomized_configs.return_value = {
        "bot1": {"mock": "config"},
        "bot2": {"mock": "config"}
    }
    
    with patch("builtins.open", mock_open()) as mocked_file, \
         patch("json.dump") as mock_json_dump, \
         patch.object(manager, '_add_bot') as mock_add_bot:
        
        manager._spawn_fleet()
        
        # 1 base + 2 random = 3 bots added ideally, but actually we set manager.max_bots = 10
        mock_randomizer.generate_randomized_configs.assert_called_once_with(
            9, strategy_type="core"
        )
        
        assert mock_add_bot.call_count == 3
        
        # Check that the base bot is added first
        call_0 = mock_add_bot.call_args_list[0]
        assert call_0.args[0] == 0
        assert call_0.args[1] == "G000_Bot_000_BASE"
        assert call_0.kwargs.get("strategy_type") == "core"
        
        # Check randomized bots
        call_1 = mock_add_bot.call_args_list[1]
        assert call_1.args[0] == 1
        assert call_1.args[1] == "G000_Bot_001"
        assert call_1.args[2] == {"mock": "config"}
        
        call_2 = mock_add_bot.call_args_list[2]
        assert call_2.args[0] == 2
        assert call_2.args[1] == "G000_Bot_002"
        assert call_2.args[2] == {"mock": "config"}

@patch("src.pulse.trading.fleet.shadow_fleet_mixins.shadow_fleet_lifecycle_mixin.VirtualBot")
@patch("src.pulse.trading.fleet.shadow_fleet_mixins.shadow_fleet_lifecycle_mixin.StrategyConfig")
def test_add_bot(mock_strategy_config, mock_virtual_bot, manager):
    # Mock objects
    mock_conf_instance = MagicMock()
    mock_conf_instance.account.starting_balance = 1000
    mock_strategy_config.return_value = mock_conf_instance
    
    mock_bot_instance = MagicMock()
    mock_bot_instance.global_state = MagicMock()
    mock_virtual_bot.return_value = mock_bot_instance
    
    manager._add_bot(index=42, name="TestBot", config_dict={}, strategy_type="core", initial_pnl=5.0, virtual_trades_completed=10)
    
    assert len(manager.bots) == 1
    assert manager.bot_index_map[42] == mock_bot_instance
    assert mock_bot_instance.fleet_index == 42
    assert mock_bot_instance.global_state.total_pnl == 5.0
    assert mock_bot_instance.global_state.current_balance == 1005.0
    assert mock_bot_instance.global_state.total_trades == 10

def _create_mock_bot(fleet_index, trades, pnl):
    bot = MagicMock()
    bot.fleet_index = fleet_index
    bot.strategy_id = f"Bot_{fleet_index}"
    bot.global_state = MagicMock()
    bot.global_state.total_trades = trades
    bot.global_state.total_pnl = pnl
    bot.global_state.win_rate = 50.0
    bot.global_state.max_drawdown = 10.0
    bot.config.raw_config = {"test": "val"}
    return bot

def test_evolve_fleet_not_enough_bots(manager):
    # Create 5 bots with 5 trades (eligible) -> less than 10 eligible
    for i in range(5):
        manager.bots.append(_create_mock_bot(i, 5, 1.0))
        
    # Should log and return early
    manager._evolve_fleet()
    assert manager.current_generation == 0

@patch("src.pulse.trading.fleet.shadow_fleet_mixins.shadow_fleet_lifecycle_mixin.GeneticOptimizer")
def test_evolve_fleet_success(mock_genetic_optimizer, manager):
    # Create 20 eligible bots
    # top 20% = 4 bots to breed
    # bottom 20% = 4 bots to kill
    
    pnl_values = list(range(1, 21)) # 1 to 20
    # Add a bit of randomness just in case, but keep it sorted so we know who dies
    
    for i, pnl in enumerate(pnl_values):
        bot = _create_mock_bot(i, 5, float(pnl))
        manager.bots.append(bot)
        manager.bot_index_map[i] = bot
        
    mock_genetic_optimizer.crossover.return_value = {"crossed": "over"}
    mock_genetic_optimizer.mutate.return_value = {"mutated": "true"}
    
    with patch("builtins.open", mock_open()) as mocked_file, \
         patch("json.dump") as mock_json_dump, \
         patch("os.path.exists", return_value=True), \
         patch("json.load", return_value={"existing": "data"}):
             
        # Patch the _add_bot method so we don't actually instantiate MagicMocks inside the class during the test
        with patch.object(manager, '_add_bot') as mock_add_bot:
            manager._evolve_fleet()
            
            assert manager.current_generation == 1
            
            # The bottom 4 bots (PnL 1, 2, 3, 4) should be dead
            assert len(manager.bots) == 16 # 20 - 4
            killed_indices = [0, 1, 2, 3]
            for idx in killed_indices:
                assert idx not in manager.bot_index_map
                
            # It should have called _add_bot 4 times to replace the killed bots
            assert mock_add_bot.call_count == 4
            
            expected_median = statistics.median([float(x) for x in range(1, 21)]) # 10.5
            
            # Check arguments for one of the add_bot calls
            # It should be re-adding bots with new indices identical to the freed ones
            added_indices = [call_args[0][0] for call_args in mock_add_bot.call_args_list]
            assert sorted(added_indices) == [0, 1, 2, 3]
            
            # Check that initial PnL equals median
            for call_args in mock_add_bot.call_args_list:
                kwargs = call_args[1]
                assert kwargs['initial_pnl'] == expected_median
                assert kwargs['virtual_trades_completed'] == 5 # min_trades
                assert "G001_Bot_" in call_args[0][1] # Bot name check
                
            # Verify crossover and mutate were called 4 times
            assert mock_genetic_optimizer.crossover.call_count == 4
            assert mock_genetic_optimizer.mutate.call_count == 4

