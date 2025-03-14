# Documentation Guide

## Core Principles

Our documentation follows these guiding principles:

1. **Tests First, Docs Alongside**: Documentation evolves with tests and implementation in the TDD cycle
2. **Single Source of Truth**: Information exists in exactly one authoritative location
3. **Practical over Theoretical**: Focus on helping developers accomplish tasks rather than explaining theory
4. **Code is the Source of Truth**: Documentation reflects code reality, not vice versa
5. **Document Why, Not Just How**: Explain the reasoning behind significant decisions

## Documentation Structure

```
docs/
├── index.md                # Project overview and quick start
├── architecture.md         # System architecture and component overview
├── development/            # Developer guides
│   ├── setup.md            # Development environment setup
│   ├── testing.md          # Testing approach (TDD)
│   ├── documentation.md    # This guide
│   ├── workflow.md         # Development workflow
│   └── examples/           # Development templates (issues, PRs, tasks)
├── components/             # One document per major component
│   ├── data_collection.md  # Data collection components
│   ├── features.md         # Feature engineering
│   └── models.md           # Model training and prediction
├── guides/                 # How-to guides for common tasks
│   └── adding_features.md  # How to add new basketball metrics
└── reference/              # Auto-generated API docs
```

**Important Note on Examples:**
This project has three distinct types of examples with specific locations:

1. **Code Examples** (`/examples` at project root)
   - Executable Python code demonstrating library usage
   - Implementation samples for pipelines, features, etc.

2. **Development Examples** (`/docs/development/examples`)
   - Templates for project management artifacts
   - Issue, PR, task, and milestone templates

3. **Documentation Examples** (`/docs/examples` if needed)
   - Examples of documentation formats
   - Only create if specifically required

## Documentation in the TDD Cycle

Documentation is integrated into each phase of Test-Driven Development:

### 1. Red Phase (Test Creation)
- Document test purpose in docstrings
- Document expected component behavior

```python
def test_calculate_point_differential():
    """
    Test that the point differential calculator:
    - Computes the difference between points scored and allowed
    - Aggregates at the team level
    - Returns correct values in a properly formatted DataFrame
    """
    # Test implementation...
```

### 2. Green Phase (Implementation)
- Write docstrings that explain what the code does
- Include type hints and parameter documentation

```python
def calculate_point_differential(game_data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate point differential for each team from game results.
    
    Args:
        game_data: DataFrame with columns [team_id, points, points_allowed]
            
    Returns:
        DataFrame with columns [team_id, point_differential]
    """
    # Implementation...
```

### 3. Refactor Phase
- Update docstrings to reflect improvements
- Document any non-obvious design decisions in comments
- Update component documentation if appropriate

## Documentation Standards

### Python Docstrings

Use Google-style docstrings for all public functions, classes, and methods:

```python
def collect_game_data(season: int, game_ids: List[str] = None) -> pl.DataFrame:
    """
    Collect NCAA basketball game data from ESPN.
    
    Args:
        season: Basketball season year (e.g., 2023 for 2022-23 season)
        game_ids: Optional list of specific game IDs to collect
            
    Returns:
        DataFrame containing raw game data
        
    Raises:
        ConnectionError: If ESPN API is unavailable
        ValueError: If season is out of range
        
    Example:
        ```python
        # Collect all games from the 2022-23 season
        games = collect_game_data(2023)
        
        # Collect specific games
        games = collect_game_data(2023, game_ids=["401468511", "401468512"])
        ```
    """
```

#### Required Elements

1. **Short description**: One-line summary of purpose
2. **Args**: All parameters with types and descriptions
3. **Returns**: Return value with type and description
4. **Raises**: Any exceptions that may be raised

#### Optional Elements (when relevant)

5. **Examples**: For complex functions or primary interfaces
6. **Notes**: For implementation details or constraints
7. **See Also**: References to related components

### Module Docstrings

Every module should have a docstring explaining its purpose:

```python
"""
Feature engineering pipeline for NCAA basketball prediction model.

This module provides components to calculate team and game-level metrics
from processed basketball data. Features are registered in a central
registry and can declare dependencies on other features.
"""
```

### Component Documentation

Component documents in `docs/components/` follow this structure:

1. **Overview**: Brief description and purpose
2. **Responsibilities**: What the component does and doesn't do
3. **Key Classes/Functions**: Major elements with descriptions
4. **Usage Examples**: Common usage patterns
5. **Data Flow**: How data moves through the component
6. **Configuration**: How to configure the component

Example component document:

```markdown
# Data Collection

## Overview
The data collection component retrieves NCAA basketball data from ESPN APIs
and stores it in Parquet format for further processing.

## Responsibilities
- Fetch game data from ESPN endpoints
- Handle rate limiting and retries
- Convert API responses to standardized DataFrame format
- Store raw data in Parquet files
- Support incremental updates for new/changed games

## Key Classes
- `ESPNClient`: Handles API communication with ESPN
- `CollectionPipeline`: Orchestrates the data collection process
- `ParquetIO`: Manages reading/writing Parquet files

## Usage Examples

```python
# Collect all games for the current season
from src.pipelines import CollectionPipeline

pipeline = CollectionPipeline()
pipeline.run(season=2023)

# Collect specific games
pipeline.run(season=2023, game_ids=["401468511", "401468512"])
```

## Data Flow
1. `ESPNClient` fetches data from ESPN endpoints
2. Data is converted to standardized DataFrame format
3. `ParquetIO` writes data to Parquet files in `data/raw/{season}/`
4. Metadata is updated to track collected games

## Configuration
Collection behavior can be configured in `configs/collection.toml`:

```toml
[espn]
base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
rate_limit = 100  # requests per minute

[storage]
data_dir = "data/"
```
```

### Guide Documents

Guide documents in `docs/guides/` follow this structure:

1. **Goal**: What the guide helps you accomplish
2. **Prerequisites**: What you need to know/have
3. **Step-by-Step Instructions**: Numbered steps
4. **Examples**: Complete working examples
5. **Troubleshooting**: Common issues and solutions

Example guide:

```markdown
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

[Example code showing complete implementation]

## Troubleshooting
- **Error: Feature dependency not found**: Ensure all dependencies are registered
- **Error: Duplicate feature name**: Each feature needs a unique name
```

## Practical Documentation Workflows

### When Creating a New Component

1. Write tests documenting expected behavior (docstrings in tests)
2. Implement with good docstrings for all public APIs
3. Create a component document if it's a major component
4. Add guide documents for common usage patterns

### When Fixing a Bug

1. Add a test demonstrating the fixed behavior
2. Update implementation with improved docstrings
3. Add to troubleshooting section in relevant guide document

### When Refactoring

1. Update docstrings to reflect new implementation
2. Ensure component documentation remains accurate
3. Update examples if interfaces change

## Documentation Tools

We use MkDocs with the Material theme for documentation:

### Building Docs

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

### Automatic API Docs

API reference is generated automatically from docstrings using `mkdocstrings`.

## Conclusion

Good documentation is a core part of our TDD process. By documenting alongside testing and implementation, we ensure that documentation stays accurate and useful. The focus is on practical, helpful content that makes development easier for both human developers and AI coding agents.