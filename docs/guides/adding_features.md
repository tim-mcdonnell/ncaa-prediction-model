# Adding a New Feature

## Goal
This guide shows you how to add a new team performance metric to the feature pipeline.

## Prerequisites
- Understanding of feature engineering concepts
- Familiar with Polars DataFrame operations
- Development environment set up

## Steps

### 1. Define the Feature Specification
Determine:
- Feature name (e.g., `offensive_efficiency`)
- Input data requirements
- Dependencies on other features
- Calculation logic

### 2. Create the Feature Test
Create a test file in `tests/features/` that defines expected behavior:

```python
def test_offensive_efficiency_feature():
    """Test the offensive efficiency feature calculation."""
    # Create test data
    test_data = create_test_data()
    
    # Calculate the feature
    calculator = OffensiveEfficiency()
    result = calculator.calculate(test_data)
    
    # Verify results
    assert "offensive_efficiency" in result.columns
    assert result.filter(pl.col("team_id") == "DUKE")["offensive_efficiency"][0] == 110.2
```

### 3. Implement the Feature Calculator
Create the feature calculator in `src/features/`:

```python
from src.features.base import FeatureCalculator

class OffensiveEfficiency(FeatureCalculator):
    """Calculate offensive efficiency (points per 100 possessions)."""
    
    name = "offensive_efficiency"
    dependencies = ["possessions"]
    
    def calculate(self, data: pl.DataFrame) -> pl.DataFrame:
        # Implementation...
        return result
```

### 4. Register the Feature
Add the feature to the registry in `src/features/__init__.py`:

```python
from src.features.registry import register
from src.features.team_performance import OffensiveEfficiency

register(OffensiveEfficiency())
```

### 5. Run the Tests
Verify your implementation passes the tests:

```bash
pytest tests/features/test_offensive_efficiency.py -v
```

## Example
Here's a complete example of adding a new "free throw rate" feature:

```python
# tests/features/test_free_throw_rate.py
import polars as pl
import pytest
from src.features.shooting import FreeThrowRateFeature
from src.utils.testing import create_test_game_data

def test_free_throw_rate_calculation():
    """Test that free throw rate is calculated correctly as FTA/FGA."""
    # Create test data with known values
    test_data = {
        "games": create_test_game_data(
            team_ids=["TEAM1", "TEAM2"],
            fta=[[20, 15], [10, 25]],  # Free throw attempts
            fga=[[80, 60], [50, 50]]   # Field goal attempts
        )
    }
    
    # Calculate the feature
    calculator = FreeThrowRateFeature()
    result = calculator.calculate(test_data)
    
    # Verify results
    assert "free_throw_rate" in result.columns
    
    # TEAM1: (20+10)/(80+50) = 30/130 = 0.2308
    assert pytest.approx(result.filter(pl.col("team_id") == "TEAM1")["free_throw_rate"][0]) == 0.2308
    
    # TEAM2: (15+25)/(60+50) = 40/110 = 0.3636
    assert pytest.approx(result.filter(pl.col("team_id") == "TEAM2")["free_throw_rate"][0]) == 0.3636

# src/features/shooting.py
import polars as pl
from src.features.base import Feature

class FreeThrowRateFeature(Feature):
    """Calculate free throw rate (FTA/FGA) for each team."""
    
    id = "free_throw_rate"
    name = "Free Throw Rate"
    description = "Free throw attempts per field goal attempt"
    
    # No dependencies on other features
    dependencies = []
    
    # Required base data
    required_data = ["games"]
    
    def calculate(self, data: dict[str, pl.DataFrame]) -> pl.DataFrame:
        games = data["games"]
        
        # Calculate totals by team
        team_stats = (
            games
            .group_by("team_id")
            .agg(
                pl.sum("fta").alias("fta_total"),
                pl.sum("fga").alias("fga_total")
            )
            .with_columns(
                (pl.col("fta_total") / pl.col("fga_total")).alias("free_throw_rate")
            )
        )
        
        return team_stats
```

## Troubleshooting
- **Error: Feature dependency not found**: Ensure all dependencies are registered before the feature that depends on them
- **Error: Duplicate feature name**: Each feature needs a unique `id` value
- **Error: Missing data columns**: Check the schema of input DataFrames against what your feature expects
- **Performance issues**: Consider using lazy evaluation with `pl.LazyFrame` for complex operations 