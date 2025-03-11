# ADR-003: Unified Data Processing Architecture with Polars

## Status

Accepted

## Date

2023-05-29

## Context

The NCAA Basketball Prediction Model includes a significant data processing and feature engineering component. We need to calculate a wide range of basketball metrics, from simple statistics (win percentages, point differentials) to complex metrics (offensive/defensive efficiency ratings, kill shots, clutch performance).

Our feature requirements include:
1. Computing over 70 basketball metrics of varying complexity (1★-5★)
2. Processing 22+ years of historical NCAA basketball data
3. Supporting time-series operations for trend analysis
4. Performing complex window calculations across games and seasons
5. Implementing various statistical adjustments for opponent strength
6. Enabling efficient integration with our DuckDB storage layer

We must choose a data processing framework that provides excellent performance, memory efficiency, and a clean API for implementing our feature engineering pipeline.

## Decision

We will adopt **Polars** as our unified data processing framework for all feature calculations and data transformations. This decision prioritizes:

1. **Performance**: Polars uses Arrow's columnar format and parallelized execution
2. **Memory Efficiency**: Better memory usage compared to Pandas for large datasets
3. **API Design**: A modern, functional, SQL-like API well-suited for analytics
4. **DuckDB Integration**: Strong compatibility with our chosen storage solution

The architecture will use:
- Polars for all data loading, transformation, and feature calculations
- Polars' lazy evaluation for optimizing complex query plans
- Direct integration between Polars and DuckDB
- Polars' native time-series functionality for temporal analysis

### Key Components:

#### 1. Feature Calculator Base Classes

```python
# src/features/base.py
from abc import ABC, abstractmethod
import polars as pl
from typing import Dict, Any, Optional, List

class Feature(ABC):
    """Base class for all feature calculators."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Feature name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Feature description."""
        pass
    
    @property
    def complexity(self) -> int:
        """Feature complexity rating (1-5)."""
        return 1
        
    @property
    def dependencies(self) -> List[str]:
        """List of features this feature depends on."""
        return []
    
    @abstractmethod
    def calculate(self, data: pl.DataFrame) -> pl.DataFrame:
        """Calculate the feature and return a DataFrame with the results."""
        pass
```

#### 2. Feature Implementation Examples

```python
# src/features/team_performance/point_differential.py
import polars as pl
from ..base import Feature

class PointDifferential(Feature):
    @property
    def name(self) -> str:
        return "point_differential"
    
    @property
    def description(self) -> str:
        return "Average margin of victory/defeat"
    
    def calculate(self, data: pl.DataFrame) -> pl.DataFrame:
        return (data
            .group_by(["team_id", "season"])
            .agg([
                (pl.mean("points") - pl.mean("points_allowed")).alias("point_differential"),
                pl.mean("points").alias("points_per_game"),
                pl.mean("points_allowed").alias("points_allowed_per_game"),
                pl.count().alias("games_played")
            ]))

# src/features/advanced_team/kill_shots.py
import polars as pl
from ..base import Feature

class KillShots(Feature):
    @property
    def name(self) -> str:
        return "kill_shots"
    
    @property
    def description(self) -> str:
        return "Number of 10-0 or better scoring runs per game"
    
    @property
    def complexity(self) -> int:
        return 4  # High complexity feature
    
    @property
    def dependencies(self) -> List[str]:
        return ["play_by_play_data"]
    
    def calculate(self, data: pl.DataFrame) -> pl.DataFrame:
        # Process play-by-play data to identify scoring runs
        # This would leverage Polars' window functions
        # Complex implementation using Polars' rolling window functionality
        return data.with_columns([
            self._detect_runs(pl.col("team_id"), pl.col("play_sequence"), pl.col("score_change"))
            .alias("kill_shots")
        ])
        
    def _detect_runs(self, team_id, play_sequence, score_change):
        # Implementation of run detection algorithm using Polars expressions
        pass
```

#### 3. Feature Pipeline Orchestration

```python
# src/features/pipeline.py
import polars as pl
from typing import Dict, List, Type
import importlib
import inspect
from .base import Feature

class FeaturePipeline:
    """Orchestrates feature calculation with dependency resolution."""
    
    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self.calculated_features: Dict[str, pl.DataFrame] = {}
        
    def register_feature(self, feature: Feature) -> None:
        """Register a feature calculator."""
        self.features[feature.name] = feature
        
    def discover_features(self, package_path: str = "src.features") -> None:
        """Auto-discover feature implementations in the specified package."""
        # Implementation to find all Feature subclasses
        pass
        
    def calculate_features(self, data: pl.DataFrame, 
                           feature_names: List[str] = None) -> Dict[str, pl.DataFrame]:
        """Calculate requested features, respecting dependencies."""
        # Implementation that resolves dependencies and calculates features
        # in the correct order, leveraging Polars' lazy evaluation
        pass
        
    def resolve_dependencies(self, feature_names: List[str]) -> List[str]:
        """Build an ordered list of features to calculate based on dependencies."""
        # Implementation of topological sort for dependency resolution
        pass
```

#### 4. Integration with DuckDB

```python
# src/data/integration.py
import polars as pl
import duckdb
from typing import List, Dict, Any

class DuckDBPolarsIntegration:
    """Provides utilities for working with DuckDB and Polars together."""
    
    def __init__(self, db_path: str):
        self.conn = duckdb.connect(db_path)
        
    def query_to_polars(self, query: str, params: Dict[str, Any] = None) -> pl.DataFrame:
        """Execute a DuckDB query and return the results as a Polars DataFrame."""
        if params:
            result = self.conn.execute(query, params)
        else:
            result = self.conn.execute(query)
        return result.pl()
    
    def save_polars_to_table(self, df: pl.DataFrame, table_name: str, mode: str = "append") -> None:
        """Save a Polars DataFrame to a DuckDB table."""
        # Directly use Polars with DuckDB
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0")
        if mode == "overwrite":
            self.conn.execute(f"DELETE FROM {table_name}")
        self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")
```

## Consequences

### Benefits

1. **Performance**: Polars provides significantly faster processing for complex features
2. **Memory Efficiency**: Lower memory footprint for large datasets
3. **Functional API**: Clean, composable code for data transformations
4. **Simplified Architecture**: A single data processing framework throughout the stack
5. **Optimized Query Planning**: Lazy evaluation for complex operations
6. **DuckDB Compatibility**: Strong integration with our storage layer

### Challenges

1. **Learning Curve**: Less familiar to some developers than Pandas
2. **Documentation**: While improving, documentation is less extensive than Pandas
3. **Ecosystem**: Smaller ecosystem than Pandas, though this is rapidly growing
4. **Edge Cases**: May encounter edge cases due to the relative youth of the library

## Alternatives Considered

### Pandas-Only Approach

**Benefits**:
- Extremely mature and well-documented
- Ubiquitous in the data science community
- Rich ecosystem of extensions and integrations
- More examples and resources available

**Drawbacks**:
- Significantly slower for complex operations
- Higher memory usage
- Less optimal for window functions and complex analytics
- Not as well-suited for larger datasets

**Rejection Rationale**: The performance and memory overhead of Pandas would limit our ability to efficiently calculate complex basketball metrics at scale. Many features like "Team Efficiency Ratings" and "Kill Shots" would be prohibitively slow.

### Hybrid Approach (Pandas + Polars)

**Benefits**:
- Use each library for its strengths
- Leverage Pandas for certain ML integrations
- Maintain compatibility with Pandas-only libraries

**Drawbacks**:
- Cognitive overhead of maintaining two similar-but-different APIs
- Conversion costs between formats
- Inconsistent patterns across the codebase
- Technical debt of mixed implementations

**Rejection Rationale**: The disadvantages of context-switching, conversion overhead, and maintaining knowledge of two similar systems outweigh the benefits. A unified approach with Polars offers a cleaner architecture and better long-term maintainability.

### Apache Spark

**Benefits**:
- Distributed processing capabilities
- Mature ecosystem
- Scales to extremely large datasets

**Drawbacks**:
- Significant overhead for our dataset size
- More complex setup and maintenance
- Slower for single-machine workloads

**Rejection Rationale**: Spark is over-engineered for our needs. The NCAA basketball dataset, even with 22+ years of data, can be efficiently processed on a single machine with Polars.

## References

- [Polars Documentation](https://pola.rs/)
- [Arrow Columnar Format](https://arrow.apache.org/)
- [DuckDB-Polars Integration](https://duckdb.org/docs/guides/python/polars.html)
- [Polars vs Pandas Benchmarks](https://h2oai.github.io/db-benchmark/)
- [Related ADR: ADR-002 Analytics-Focused Data Storage with DuckDB](adr-002-data-storage.md) 