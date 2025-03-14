"""
Pipeline Composition Example

This example demonstrates how to compose multiple pipelines
into a single pipeline for sequential execution.
"""

import asyncio

import polars as pl

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.pipeline_composition import ComposedPipeline
from src.utils.logging import get_pipeline_logger

# Set up logging
logger = get_pipeline_logger("pipeline_composition_example")


class DataFilterPipeline(BasePipeline):
    """
    A pipeline that filters data based on a condition.
    
    This pipeline keeps rows where a specific column value 
    meets the given condition.
    """
    
    def __init__(self, filter_col: str, min_value: float):
        """
        Initialize the filter pipeline.
        
        Args:
            filter_col: The column to filter on
            min_value: Minimum value to keep (inclusive)
        """
        super().__init__()
        self.filter_col = filter_col
        self.min_value = min_value
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate that the input data exists and has the required column."""
        if "data" not in context.input_data:
            logger.error("Missing required input data")
            return False
            
        input_df = context.input_data["data"]
        if not isinstance(input_df, pl.DataFrame):
            logger.error("Input data must be a Polars DataFrame")
            return False
            
        if self.filter_col not in input_df.columns:
            logger.error(f"Input data missing required column: {self.filter_col}")
            return False
            
        return True
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Filter the data based on the configured condition."""
        input_df = context.input_data["data"]
        
        # Apply filter
        result_df = input_df.filter(pl.col(self.filter_col) >= self.min_value)
        
        logger.info(f"Filtered data from {len(input_df)} to {len(result_df)} rows")
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={
                "filter_column": self.filter_col,
                "min_value": self.min_value,
                "input_rows": len(input_df),
                "output_rows": len(result_df)
            }
        )
        
    async def _cleanup(self) -> None:
        """No resources to clean up."""
        pass


class DataTransformPipeline(BasePipeline):
    """
    A pipeline that transforms data by applying calculations.
    
    This pipeline adds new columns based on calculations on existing columns.
    """
    
    def __init__(self, source_col: str, target_col: str, multiplier: float):
        """
        Initialize the transform pipeline.
        
        Args:
            source_col: The source column for calculations
            target_col: The new column to create
            multiplier: Value to multiply the source column by
        """
        super().__init__()
        self.source_col = source_col
        self.target_col = target_col
        self.multiplier = multiplier
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate that the input data exists and has the required column."""
        if "data" not in context.input_data:
            logger.error("Missing required input data")
            return False
            
        input_df = context.input_data["data"]
        if not isinstance(input_df, pl.DataFrame):
            logger.error("Input data must be a Polars DataFrame")
            return False
            
        if self.source_col not in input_df.columns:
            logger.error(f"Input data missing required column: {self.source_col}")
            return False
            
        return True
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Transform the data by adding the new calculated column."""
        input_df = context.input_data["data"]
        
        # Apply transformation
        result_df = input_df.with_columns(
            (pl.col(self.source_col) * self.multiplier).alias(self.target_col)
        )
        
        logger.info(f"Added calculated column: {self.target_col}")
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={
                "source_column": self.source_col,
                "target_column": self.target_col,
                "multiplier": self.multiplier
            }
        )
        
    async def _cleanup(self) -> None:
        """No resources to clean up."""
        pass


class DataAggregationPipeline(BasePipeline):
    """
    A pipeline that aggregates data by grouping.
    
    This pipeline groups data by a specified column and 
    aggregates other columns.
    """
    
    def __init__(self, group_col: str, agg_cols: list[str]):
        """
        Initialize the aggregation pipeline.
        
        Args:
            group_col: The column to group by
            agg_cols: Columns to aggregate (sum)
        """
        super().__init__()
        self.group_col = group_col
        self.agg_cols = agg_cols
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate that the input data exists and has the required columns."""
        if "data" not in context.input_data:
            logger.error("Missing required input data")
            return False
            
        input_df = context.input_data["data"]
        if not isinstance(input_df, pl.DataFrame):
            logger.error("Input data must be a Polars DataFrame")
            return False
            
        if self.group_col not in input_df.columns:
            logger.error(f"Input data missing required column: {self.group_col}")
            return False
            
        for col in self.agg_cols:
            if col not in input_df.columns:
                logger.error(f"Input data missing required column: {col}")
                return False
            
        return True
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Aggregate the data by grouping."""
        input_df = context.input_data["data"]
        
        # Create aggregation expressions
        agg_exprs = [pl.sum(col).alias(f"sum_{col}") for col in self.agg_cols]
        
        # Apply aggregation
        result_df = input_df.group_by(self.group_col).agg(*agg_exprs)
        
        logger.info(f"Aggregated data from {len(input_df)} to {len(result_df)} rows")
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={
                "group_column": self.group_col,
                "agg_columns": self.agg_cols,
                "input_rows": len(input_df),
                "output_rows": len(result_df)
            }
        )
        
    async def _cleanup(self) -> None:
        """No resources to clean up."""
        pass


async def run_example():
    """Run an example of pipeline composition."""
    # Create sample data - basketball team stats
    input_df = pl.DataFrame({
        "team_id": [1, 1, 1, 2, 2, 3, 3, 3, 4, 4],
        "game_id": [101, 102, 103, 101, 104, 102, 103, 105, 104, 105],
        "points": [68, 75, 82, 65, 70, 72, 85, 90, 68, 73],
        "rebounds": [35, 30, 42, 28, 33, 31, 38, 40, 25, 29]
    })
    
    print("\nInput Data:")
    print(input_df)
    
    # Create individual pipelines
    filter_pipeline = DataFilterPipeline(filter_col="points", min_value=70)
    transform_pipeline = DataTransformPipeline(
        source_col="rebounds",
        target_col="rebound_score",
        multiplier=0.5
    )
    agg_pipeline = DataAggregationPipeline(
        group_col="team_id",
        agg_cols=["points", "rebounds", "rebound_score"]
    )
    
    # Compose pipelines into a single workflow
    composed_pipeline = ComposedPipeline(
        name="team_stats_analysis",
        pipelines=[filter_pipeline, transform_pipeline, agg_pipeline]
    )
    
    # Create context and execute
    context = PipelineContext(input_data={"data": input_df})
    result = await composed_pipeline.execute(context)
    
    # Print results
    print("\nPipeline Composition Results:")
    print(f"Status: {result.status.name}")
    print("Metadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")
    
    # Check if we have result data before printing it
    if "result" in result.output_data:
        print("\nOutput Data:")
        print(result.output_data["result"])
    else:
        print("\nNo output data available (pipeline didn't complete successfully)")
    
    # Clean up
    await composed_pipeline.cleanup()
    
    # Also demonstrate individual pipeline execution for comparison
    print("\nExecuting pipelines individually for comparison:")
    
    # Filter
    filter_context = PipelineContext(input_data={"data": input_df})
    filter_result = await filter_pipeline.execute(filter_context)
    filter_df = filter_result.output_data["result"]
    print("\nAfter filtering (points >= 70):")
    print(filter_df)
    
    # Transform filtered data
    transform_context = PipelineContext(input_data={"data": filter_df})
    transform_result = await transform_pipeline.execute(transform_context)
    transform_df = transform_result.output_data["result"]
    print("\nAfter transforming (added rebound_score):")
    print(transform_df)
    
    # Aggregate transformed data
    agg_context = PipelineContext(input_data={"data": transform_df})
    agg_result = await agg_pipeline.execute(agg_context)
    agg_df = agg_result.output_data["result"]
    print("\nAfter aggregating (by team_id):")
    print(agg_df)


if __name__ == "__main__":
    # Set up asyncio to run the example
    asyncio.run(run_example()) 