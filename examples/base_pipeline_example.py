#!/usr/bin/env python3
"""
Base Pipeline Framework Example

This example demonstrates how to use the base pipeline framework to create
a custom pipeline with error handling, retry functionality, and state management.
"""

import asyncio
import logging
import random

import polars as pl

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataTransformPipeline(BasePipeline):
    """
    Example pipeline that transforms data.
    
    This pipeline demonstrates:
    - Input validation
    - Data transformation
    - Error handling
    - Resource cleanup
    - State management
    """
    
    def __init__(self, retry_enabled: bool = False):
        """
        Initialize the pipeline.
        
        Args:
            retry_enabled: Whether to enable automatic retry on failure
        """
        super().__init__(
            retry_enabled=retry_enabled,
            max_retry_attempts=3,
            retry_backoff_factor=1.5,
            retry_jitter=0.2
        )
        self.resources = []
        logger.info("Initialized DataTransformPipeline")
    
    async def _validate(self, context: PipelineContext) -> bool:
        """
        Validate the pipeline input.
        
        Checks that the required parameters and input data are present.
        
        Args:
            context: Pipeline execution context
            
        Returns:
            True if valid, False otherwise
        """
        # Check required parameters
        if "output_column" not in context.params:
            logger.error("Missing required parameter: output_column")
            return False
            
        # Check required input data
        if "data" not in context.input_data:
            logger.error("Missing required input data: data")
            return False
            
        # Check data format
        if not isinstance(context.input_data["data"], pl.DataFrame):
            logger.error("Input data must be a polars DataFrame")
            return False
            
        # Check required columns
        required_columns = ["value"]
        data = context.input_data["data"]
        for column in required_columns:
            if column not in data.columns:
                logger.error(f"Missing required column: {column}")
                return False
                
        logger.info("Validation successful")
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """
        Execute the data transformation pipeline.
        
        Performs the following steps:
        1. Extract input data and parameters
        2. Transform the data
        3. Return the result
        
        Args:
            context: Pipeline execution context
            
        Returns:
            Pipeline execution result
        """
        # Extract input data and parameters
        data = context.input_data["data"]
        output_column = context.params["output_column"]
        
        # Simulate resource allocation
        resource_id = f"resource_{random.randint(1000, 9999)}"
        self.resources.append(resource_id)
        logger.info(f"Allocated resource: {resource_id}")
        
        # Simulate potential failure (80% chance)
        if context.params.get("simulate_failures", False) and random.random() < 0.8:
            logger.warning("Simulating random failure")
            raise RuntimeError("Simulated failure during processing")
        
        # Perform transformation
        logger.info(f"Transforming data ({len(data)} rows)")
        
        # Double the value and store in new column
        result_df = data.with_columns(
            pl.col("value").mul(2).alias(output_column)
        )
        
        # Add metadata
        metadata = {
            "input_rows": len(data),
            "output_rows": len(result_df),
            "transformation": "double_value",
            "resources": self.resources.copy()
        }
        
        logger.info(f"Transformation complete: {metadata}")
        
        # Return success result
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"transformed_data": result_df},
            metadata=metadata
        )
    
    async def _cleanup(self) -> None:
        """
        Clean up allocated resources.
        
        This method is called regardless of whether execution succeeded or failed.
        """
        if self.resources:
            logger.info(f"Cleaning up {len(self.resources)} resources")
            for resource_id in self.resources:
                logger.info(f"Released resource: {resource_id}")
            self.resources.clear()
        else:
            logger.info("No resources to clean up")


async def run_example(retry_enabled: bool = False, simulate_failures: bool = False):
    """
    Run the example pipeline.
    
    Args:
        retry_enabled: Whether to enable automatic retry
        simulate_failures: Whether to simulate random failures
    """
    logger.info(f"Running example (retry_enabled={retry_enabled}, "
                f"simulate_failures={simulate_failures})")
    
    # Create sample data
    data = pl.DataFrame({
        "id": range(1, 6),
        "value": [10, 20, 30, 40, 50]
    })
    
    # Create pipeline context
    context = PipelineContext(
        params={
            "output_column": "doubled_value",
            "simulate_failures": simulate_failures
        },
        input_data={"data": data}
    )
    
    # Create and execute pipeline
    pipeline = DataTransformPipeline(retry_enabled=retry_enabled)
    result = await pipeline.execute(context)
    
    # Check result
    if result.status == PipelineStatus.SUCCESS:
        output_data = result.output_data["transformed_data"]
        logger.info(f"Pipeline succeeded with {len(output_data)} rows of data")
        logger.info(f"Sample output:\n{output_data.head()}")
    else:
        logger.error(f"Pipeline failed with status: {result.status.name}")
        if result.error:
            logger.error(f"Error: {type(result.error).__name__}: {str(result.error)}")
    
    # Get final state
    state = pipeline.get_state()
    logger.info(f"Final pipeline state: {state.status.name}")
    logger.info(f"Execution time: {state.execution_time:.3f} seconds")
    
    # Clean up
    await pipeline.cleanup()
    
    return result


if __name__ == "__main__":
    """
    Run the examples.
    
    This demonstrates:
    1. Basic pipeline execution
    2. Pipeline with simulated failures, no retry
    3. Pipeline with simulated failures and retry enabled
    """
    # Run examples
    logger.info("=== Example 1: Basic execution ===")
    asyncio.run(run_example())
    
    logger.info("\n=== Example 2: With failures, no retry ===")
    asyncio.run(run_example(retry_enabled=False, simulate_failures=True))
    
    logger.info("\n=== Example 3: With failures and retry enabled ===")
    asyncio.run(run_example(retry_enabled=True, simulate_failures=True)) 