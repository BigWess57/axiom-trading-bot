# Shadow Fleet: Natural Selection & Genetic Algorithm

This document outlines the architecture and implementation of the continuous "natural selection" evolutionary mechanics operating within the Shadow Fleet.

## Overview

The Shadow Fleet continuously trades a massive array of virtual bots with slightly randomized strategy configurations. To ensure the fleet adapts to changing market conditions and zeroes in on the most optimal parameters, the system uses a **Genetic Algorithm** to cull poorly performing bots and breed new offspring from the most successful bots.

## Key Components

### 1. `GeneticOptimizer` (`src/pulse/trading/fleet/genetic_optimizer.py`)
Provides the core mathematical operations for digital breeding:
*   **Crossover**: Takes two parent configuration dictionaries and randomly selects attributes from either parent to construct a new child config. The selection is randomized per attribute block.
*   **Mutation**: Randomly nudges float/int values in the child config by a defined variance (e.g., +/- 10%) based on a mutation rate probability. This ensures genetic diversity and prevents the fleet from getting permanently stuck in a local maximum.

### 2. `ShadowFleetLifecycleMixin` (`src/pulse/trading/fleet/mixins/shadow_fleet_lifecycle_mixin.py`)
The orchestrated evolutionary loop and lifecycle manager.
*   **Fixed Slots (`fleet_index`)**: The fleet maintains a strict, capped size (e.g., 500 bots), assigning each bot a permanent index from `000` to `499`.
*   **Generational Naming**: Bots are named with a generation prefix (e.g., `G000_Bot_042`). When a bot dies and its slot is filled by a child in the next generation, the new bot inherits the index but increments the generation counter (`G001_Bot_042`).
*   **Generational Loop**: A background asynchronous loop wakes up every `N` minutes to execute an evolution cycle.

### 3. Evolutionary Mechanics (`_evolve_fleet`)
1.  **Eligibility**: Bots must have completed a minimum number of virtual trades (e.g., 5) to be considered for evolution.
2.  **Ranking**: Bots are sorted by `total_pnl`.
3.  **Selection (Tournament/Elitism)**: 
    *   The bottom **20%** of the eligible population is marked as "losers" and killed. Their state is cleared, and their memory slots are freed.
    *   The top **20%** of the eligible population is marked as "elites".
4.  **Crossover & Mutation**: For every empty slot left by a dead bot, two parents are randomly selected from the elite pool to breed a new child config.
5.  **Rebirth**: The new children spawn into the exact fleet slot indexes of the dead bots.
6.  **Fair Start**: To prevent new children from being instantly culled due to having a starting PnL of 0 (while the rest of the fleet is far ahead), children inherit the **median `total_pnl`** of the current fleet.

### 4. Continuous Logging Ecosystem
To support Machine Learning and deep data analysis, all configs and metrics are safely logged as the generations progress:
*   **Master Config File (`data/config_logs/fleet_configs_{timestamp}.json`)**: A single JSON dictionary maintained for the entire session. Every time a new child is born, its unique strategy ID (e.g., `G007_Bot_251`) and full config dict are appended to this master file. This allows standard `analyze_fleet.py` scripts to instantly map a bot's trades to its exact generational settings.
*   **Leaderboard Tracker (`data/config_logs/leaderboard_{timestamp}.txt`)**: At the end of every generation, the system appends the Generation ID, Median Fleet PnL, and a printed leaderboard of the Top 10 Elite Bots.

## Result

The Shadow Fleet acts as an unsupervised, highly parallel machine learning engine. It constantly tests hundreds of configurations against live token data in real-time, instantly pruning failed experiments and iteratively zeroing in on highly profitable strategies.
