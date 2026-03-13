import pytest
from src.pulse.trading.fleet.genetic_optimizer import GeneticOptimizer

def test_crossover_configs():
    parent1 = {"min_market_cap": 8000.0, "max_holding_time": 300}
    parent2 = {"min_market_cap": 12000.0, "max_holding_time": 600}
    
    child = GeneticOptimizer.crossover(parent1, parent2)
    
    assert child["min_market_cap"] in (8000.0, 12000.0)
    assert child["max_holding_time"] in (300, 600)

def test_mutate_config():
    config = {"min_market_cap": 10000.0, "max_holding_time": 300}
    
    # Mutate with 100% rate and small variance
    mutated = GeneticOptimizer.mutate(config, mutation_rate=1.0, max_variance=0.10)
    
    assert isinstance(mutated["min_market_cap"], float)
    assert 9000.0 <= mutated["min_market_cap"] <= 11000.0
