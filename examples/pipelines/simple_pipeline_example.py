"""
Simple Pipeline Example

This module demonstrates how to implement a concrete pipeline
using the BasePipeline framework.
"""

import asyncio
import logging
import polars as pl
from typing import Dict, Any, Optional

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus
)
from src.utils.logging import get_pipeline_logger

# Set up logging
logger = get_pipeline_logger("simple_pipeline_example")


class SimplePipeline(BasePipeline):
    """
    A simple example pipeline that demonstrates the base pipeline framework.
    
    This pipeline:
    1. Takes input DataFrame(s)
    2. Performs a simple transformation
    3. Returns the transformed data
    """
    
    def __init__(self, transform_type: str = "filter"):
        """
        Initialize the simple pipeline.
        
        Args:
            transform_type: The type of transformation to perform
                (options: "filter", "aggregate", "join")
        """
        super().__init__()
        self.transform_type = transform_type
        logger.info(f"Initialized SimplePipeline with transform_type={transform_type}")
    
    async def _validate(self, context: PipelineContext) -> bool:
        """
        Validate the pipeline context.
        
        Checks that:
        - Required input data is present
        - Transform type is valid
        
        Args:
            context: Execution context
            
        Returns:
            True if valid, False otherwise
        """
        # Check that input data contains the 'data' key
        if "data" not in context.input_data:
            logger.error("Missing required input data with key 'data'")
            return False
        
        # Check that the input data is a DataFrame
        if not isinstance(context.input_data["data"], pl.DataFrame):
            logger.error("Input data must be a Polars DataFrame")
            return False
        
        # Check that the transform type is valid
        valid_transform_types = ["filter", "aggregate", "join"]
        if self.transform_type not in valid_transform_types:
            logger.error(f"Invalid transform type: {self.transform_type}. "
                         f"Must be one of {valid_transform_types}")
            return False
        
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """
        Execute the pipeline.
        
        Performs the specified transformation on the input data.
        
        Args:
            context: Execution context with input data
            
        Returns:
            PipelineResult with transformed data
        """
        logger.info(f"Executing SimplePipeline with transform_type={self.transform_type}")
        
        # Get input data
        input_df = context.input_data["data"]
        
        # Perform transformation based on transform_type
        if self.transform_type == "filter":
            # Filter rows where the first column > 0
            first_col = input_df.columns[0]
            result_df = input_df.filter(pl.col(first_col) > 0)
            logger.info(f"Filtered data: {len(input_df)} -> {len(result_df)} rows")
            
        elif self.transform_type == "aggregate":
            # Group by the first column and aggregate the others
            group_col = input_df.columns[0]
            agg_cols = input_df.columns[1:]
            
            if not agg_cols:
                logger.warning("No columns to aggregate")
                result_df = input_df
            else:
                agg_exprs = [pl.sum(col).alias(f"sum_{col}") for col in agg_cols]
                result_df = input_df.group_by(group_col).agg(*agg_exprs)
                logger.info(f"Aggregated data: {len(input_df)} -> {len(result_df)} rows")
                
        elif self.transform_type == "join":
            # If secondary data is provided, join with it
            if "secondary_data" not in context.input_data:
                logger.warning("No secondary data for join, returning input data")
                result_df = input_df
            else:
                secondary_df = context.input_data["secondary_data"]
                join_col = input_df.columns[0]  # Join on first column
                
                if join_col not in secondary_df.columns:
                    logger.warning(f"Join column {join_col} not in secondary data")
                    result_df = input_df
                else:
                    result_df = input_df.join(
                        secondary_df, on=join_col, how="inner"
                    )
                    logger.info(f"Joined data: {len(result_df)} rows")
        
        # Create a successful result
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={
                "transform_type": self.transform_type,
                "input_rows": len(input_df),
                "output_rows": len(result_df)
            }
        )
    
    async def _cleanup(self) -> None:
        """Clean up any resources used by the pipeline."""
        # This is a simple pipeline with no resources to clean up
        logger.debug("No resources to clean up")


async def run_example():
    """Run a simple example of the pipeline."""
    # Create input data
    input_df = pl.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "value": [10, -5, 20, -15, 30]
    })
    
    # Create pipeline context
    context = PipelineContext(
        params={"example": True},
        input_data={"data": input_df}
    )
    
    # Create and execute pipeline
    pipeline = SimplePipeline(transform_type="filter")
    result = await pipeline.execute(context)
    
    # Print results
    print("\nPipeline Example Results:")
    print(f"Status: {result.status.name}")
    print(f"Metadata: {result.metadata}")
    print("Output Data:")
    print(result.output_data["result"])
    
    # Clean up
    await pipeline.cleanup()


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example()) 