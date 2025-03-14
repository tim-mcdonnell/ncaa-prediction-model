# Extending the Pipeline Framework

## Goal
This guide shows you how to extend the pipeline framework by creating a new pipeline component, composing pipelines, adding dependency injection, and implementing custom monitoring.

## Prerequisites
- Understanding of the pipeline architecture (see `docs/architecture.md`)
- Familiar with async/await programming in Python
- Development environment set up

## Steps

### 1. Define the Pipeline Specification
Determine:
- Pipeline purpose and name (e.g., `TeamMetricsPipeline`)
- Input data requirements and output format
- Dependencies on other components
- Validation criteria

### 2. Create the Pipeline Test
Create a test file in `tests/pipelines/` that defines expected behavior:

```python
import pytest
import polars as pl
from src.pipelines.team_metrics import TeamMetricsPipeline
from src.pipelines.base_pipeline import PipelineContext, PipelineStatus

@pytest.mark.asyncio
async def test_team_metrics_pipeline():
    """Test that the team metrics pipeline correctly calculates team statistics."""
    # Create test data
    test_data = pl.DataFrame({
        "team_id": ["TEAM1", "TEAM1", "TEAM2", "TEAM2"],
        "game_id": ["G1", "G2", "G1", "G3"],
        "points": [70, 85, 65, 90],
        "opponent_points": [65, 80, 70, 78],
    })
    
    # Create context with input data
    context = PipelineContext(
        input_data={"games": test_data},
        params={"metrics": ["scoring", "margin"]}
    )
    
    # Create and execute pipeline
    pipeline = TeamMetricsPipeline()
    result = await pipeline.execute(context)
    
    # Verify results
    assert result.status == PipelineStatus.SUCCESS
    assert "team_stats" in result.output_data
    
    stats_df = result.output_data["team_stats"]
    assert "team_id" in stats_df.columns
    assert "avg_points" in stats_df.columns
    assert "point_margin" in stats_df.columns
    
    # Check specific values
    team1_stats = stats_df.filter(pl.col("team_id") == "TEAM1")
    assert team1_stats["avg_points"][0] == 77.5  # (70 + 85) / 2
    assert team1_stats["point_margin"][0] == 5.0  # ((70-65) + (85-80)) / 2
```

### 3. Implement the Pipeline Class
Create the pipeline implementation in `src/pipelines/`:

```python
from src.pipelines.base_pipeline import BasePipeline, PipelineContext, PipelineResult, PipelineStatus
import polars as pl
from typing import List, Dict, Any

class TeamMetricsPipeline(BasePipeline):
    """Calculate team-level metrics from game data."""
    
    def __init__(self):
        super().__init__()
    
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate input data has required columns."""
        if "games" not in context.input_data:
            self._log_error("Input data missing 'games' DataFrame")
            return False
            
        games_df = context.input_data["games"]
        required_cols = ["team_id", "game_id", "points"]
        
        has_required = all(col in games_df.columns for col in required_cols)
        if not has_required:
            self._log_error(f"Games data missing required columns: {required_cols}")
            
        return has_required
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Calculate requested team metrics."""
        games_df = context.input_data["games"]
        requested_metrics = context.params.get("metrics", ["scoring"])
        
        # Start with base groupby
        result_df = games_df.group_by("team_id")
        
        # Add metrics based on request
        aggs = []
        
        if "scoring" in requested_metrics:
            aggs.append(pl.mean("points").alias("avg_points"))
            
        if "margin" in requested_metrics and "opponent_points" in games_df.columns:
            # Create point differential column
            games_df = games_df.with_columns(
                (pl.col("points") - pl.col("opponent_points")).alias("point_diff")
            )
            aggs.append(pl.mean("point_diff").alias("point_margin"))
            
        # Apply aggregations
        if not aggs:
            return PipelineResult(
                status=PipelineStatus.ERROR,
                error_message="No valid metrics requested"
            )
            
        result_df = games_df.group_by("team_id").agg(aggs)
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"team_stats": result_df},
            metadata={"metrics_calculated": requested_metrics}
        )
        
    async def _cleanup(self) -> None:
        """No resources to clean up."""
        pass
```

### 4. Compose with Other Pipelines (Optional)
Create a composed pipeline combining multiple components:

```python
from src.pipelines.pipeline_composition import ComposedPipeline
from src.pipelines.data_loader import GameDataLoader
from src.pipelines.team_metrics import TeamMetricsPipeline

# Create individual pipelines
data_loader = GameDataLoader(source="parquet")
metrics_pipeline = TeamMetricsPipeline()

# Compose them into a single pipeline
analysis_pipeline = ComposedPipeline(
    name="team_analysis",
    pipelines=[data_loader, metrics_pipeline]
)

# Usage:
# context = PipelineContext(params={"season": 2023, "metrics": ["scoring", "margin"]})
# result = await analysis_pipeline.execute(context)
```

### 5. Add Dependency Injection (Optional)
Use dependency injection for external dependencies:

```python
from src.pipelines.dependency_injection import injectable, Dependency
from typing import Protocol

# Define protocol for a dependency
class DataWriter(Protocol):
    async def write(self, data: Dict[str, pl.DataFrame], path: str) -> bool: ...

# Create a pipeline with injectable dependencies
class DataExportPipeline(BasePipeline):
    @injectable
    def __init__(self, writer: DataWriter):
        super().__init__()
        self.writer = writer
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        output_path = context.params.get("output_path", "data/stats.parquet")
        success = await self.writer.write(context.input_data, output_path)
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS if success else PipelineStatus.FAILURE,
            metadata={"output_path": output_path}
        )
```

### 6. Add Custom Monitoring (Optional)
Create a custom monitor for your pipeline:

```python
from src.pipelines.monitoring import PipelineMonitor, MonitoringEvent, register_monitor
import logging

class MetricsMonitor(PipelineMonitor):
    def __init__(self):
        self.logger = logging.getLogger("metrics_monitor")
        handler = logging.FileHandler("metrics_pipeline.log")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def record_event(self, event: MonitoringEvent) -> None:
        if event.event_type == "pipeline_start":
            self.logger.info(f"Starting pipeline: {event.pipeline_name}")
        
        elif event.event_type == "pipeline_end":
            duration = event.data.get("execution_time_ms", 0)
            status = event.data.get("status", "UNKNOWN")
            self.logger.info(
                f"Pipeline {event.pipeline_name} completed with status {status} "
                f"in {duration}ms"
            )
            
            # Log calculated metrics if available
            if "metrics_calculated" in event.data:
                self.logger.info(f"Metrics calculated: {event.data['metrics_calculated']}")
                
        elif event.event_type == "pipeline_error":
            self.logger.error(
                f"Error in pipeline {event.pipeline_name}: {event.data.get('message', 'Unknown error')}"
            )

# Register the monitor with the framework
register_monitor(MetricsMonitor())
```

### 7. Run the Pipeline Tests
Verify your implementation passes the tests:

```bash
pytest tests/pipelines/test_team_metrics_pipeline.py -v
```

## Example
Here's a complete example of creating a data transformation pipeline:

```python
# tests/pipelines/test_data_transform_pipeline.py
import pytest
import polars as pl
from src.pipelines.base_pipeline import PipelineContext
from src.pipelines.transforms import DataTransformPipeline

@pytest.mark.asyncio
async def test_data_transform_pipeline():
    # Create test data
    input_df = pl.DataFrame({
        "team_id": ["TEAM1", "TEAM2"],
        "wins": [20, 15],
        "losses": [10, 15],
    })
    
    # Create pipeline with transformation function
    pipeline = DataTransformPipeline(
        transforms=[
            # Add win percentage
            lambda df: df.with_columns(
                (pl.col("wins") / (pl.col("wins") + pl.col("losses"))).alias("win_pct")
            ),
            # Add win-loss differential
            lambda df: df.with_columns(
                (pl.col("wins") - pl.col("losses")).alias("win_diff")
            )
        ]
    )
    
    # Execute pipeline
    context = PipelineContext(input_data={"teams": input_df})
    result = await pipeline.execute(context)
    
    # Verify results
    output_df = result.output_data["teams"]
    assert "win_pct" in output_df.columns
    assert "win_diff" in output_df.columns
    
    # Check specific values
    team1 = output_df.filter(pl.col("team_id") == "TEAM1")
    assert team1["win_pct"][0] == 0.6666666666666666  # 20/(20+10)
    assert team1["win_diff"][0] == 10  # 20-10

# src/pipelines/transforms.py
from src.pipelines.base_pipeline import BasePipeline, PipelineContext, PipelineResult, PipelineStatus
import polars as pl
from typing import List, Callable, Dict

class DataTransformPipeline(BasePipeline):
    """Pipeline for applying a series of transformations to input data."""
    
    def __init__(self, transforms: List[Callable[[pl.DataFrame], pl.DataFrame]]):
        """
        Initialize the transform pipeline.
        
        Args:
            transforms: List of transformation functions to apply sequentially
        """
        super().__init__()
        self.transforms = transforms
    
    async def _validate(self, context: PipelineContext) -> bool:
        """Check if there is any DataFrame in the input data."""
        if not context.input_data:
            self._log_error("No input data provided")
            return False
        
        # Check that at least one value is a DataFrame
        has_dataframe = any(
            isinstance(value, pl.DataFrame) 
            for value in context.input_data.values()
        )
        
        if not has_dataframe:
            self._log_error("No DataFrames found in input data")
            return False
            
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Apply transformations to all DataFrames in input data."""
        result_data = {}
        
        for key, value in context.input_data.items():
            if isinstance(value, pl.DataFrame):
                # Apply all transformations in sequence
                result_df = value
                for transform_fn in self.transforms:
                    result_df = transform_fn(result_df)
                
                result_data[key] = result_df
            else:
                # Keep non-DataFrame values as is
                result_data[key] = value
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data=result_data,
            metadata={"num_transforms": len(self.transforms)}
        )
        
    async def _cleanup(self) -> None:
        """No resources to clean up."""
        pass
```

## Troubleshooting

- **Error: Pipeline validation failed**: Check that your input data matches what the pipeline expects
- **Error: Dependency not found**: Ensure all dependencies are registered with the dependency registry
- **Warning: Pipeline leaking resources**: Make sure to clean up all resources in the `_cleanup` method
- **Performance issue: Pipeline too slow**: Consider adding more detailed timing events and use a timing monitor to identify bottlenecks:

```python
# Add timing events in your pipeline
async def _execute(self, context: PipelineContext) -> PipelineResult:
    self._broadcast_event("operation_start", {"operation": "data_load"})
    data = await self._load_data()
    self._broadcast_event("operation_end", {"operation": "data_load"})
    
    self._broadcast_event("operation_start", {"operation": "transformation"})
    result = self._transform(data)
    self._broadcast_event("operation_end", {"operation": "transformation"})
    
    return PipelineResult(status=PipelineStatus.SUCCESS, output_data={"result": result})
```

- **Composition problem: Later pipeline not receiving data**: Check that each pipeline correctly names its output data keys to match what subsequent pipelines expect

## Next Steps

After extending the pipeline framework:

1. Integrate your new pipeline with the broader system
2. Add appropriate error handling and logging
3. Consider performance optimizations
4. Update the documentation with new examples
5. Create unit and integration tests for the complete workflow 