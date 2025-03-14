# Feature Engineering

## Overview
The feature engineering component calculates basketball metrics from processed game data. It handles feature dependencies and ensures features are calculated in the correct order.

## Responsibilities
- Calculate team and player performance metrics
- Manage dependencies between features
- Organize features in a registry
- Support incremental calculation for changed data
- Save features in standardized formats

## Key Classes
- `Feature`: Base class for all feature calculators
- `FeatureRegistry`: Central registry of available features
- `FeaturePipeline`: Orchestrates feature calculation with dependency resolution
- `FeatureLoader`: Loads and combines features for model training

## Usage Examples

```python
# Calculate all features
from src.pipelines import FeaturePipeline

pipeline = FeaturePipeline()
pipeline.calculate_features()

# Calculate specific features
pipeline.calculate_features(
    feature_ids=["team_offensive_efficiency", "team_defensive_efficiency"]
)

# Calculate features for specific seasons
pipeline.calculate_features(
    seasons=[2023, 2024]
)
```

## Feature Categories

### Team Features
- Offensive efficiency (points per 100 possessions)
- Defensive efficiency (points allowed per 100 possessions)
- Four factors (shooting, turnovers, rebounding, free throws)
- Tempo (possessions per 40 minutes)

### Player Features
- Box score statistics (points, rebounds, assists, etc.)
- Advanced metrics (PER, true shooting percentage, etc.)
- Play-by-play derived metrics (plus-minus, lineup impact)

## Adding New Features

Features are implemented as classes that inherit from the `Feature` base class:

```python
from src.features.base import Feature

class OffensiveEfficiencyFeature(Feature):
    id = "team_offensive_efficiency"
    name = "Team Offensive Efficiency"
    description = "Points scored per 100 possessions"
    
    # Dependencies on other features
    dependencies = ["team_possessions"]
    
    # Required base data
    required_data = ["games", "teams"]
    
    def calculate(self, data):
        # Implementation details
        # ...
```

See the [Adding Features Guide](../guides/adding_features.md) for detailed instructions.

## Configuration
Feature calculation can be configured in `configs/features.toml`:

```toml
[calculation]
parallel = true
max_workers = 4

[storage]
cache_enabled = true
``` 