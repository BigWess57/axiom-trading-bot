import random
from typing import Dict, Any

class GeneticOptimizer:
    @staticmethod
    def crossover(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a child config by randomly selecting attributes from two parents."""
        child = {}
        for key in parent1.keys():
            if key in parent2:
                child[key] = parent1[key] if random.random() > 0.5 else parent2[key]
            else:
                child[key] = parent1[key]
        return child
        
    @staticmethod
    def mutate(config: Dict[str, Any], mutation_rate: float = 0.2, max_variance: float = 0.05) -> Dict[str, Any]:
        """Randomly varies numerical parameters in the config."""
        mutated = config.copy()
        for key, value in mutated.items():
            if random.random() < mutation_rate:
                if isinstance(value, bool):
                    mutated[key] = not value
                elif isinstance(value, float):
                    variation = value * random.uniform(-max_variance, max_variance)
                    mutated[key] = round(value + variation, 2)
                elif isinstance(value, int):
                    # For ints, ensure at least +/- 1 variation if it mutates
                    variation = max(1, abs(int(value * max_variance)))
                    sign = random.choice([-1, 1])
                    mutated[key] = int(value + (variation * sign))
        return mutated
