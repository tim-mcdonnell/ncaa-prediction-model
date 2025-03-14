"""
Dependency Injection Example

This example demonstrates how to use dependency injection
with pipeline components for easier testing and extensibility.
"""

import asyncio
from typing import Protocol

import polars as pl

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.dependency_injection import Dependency, injectable
from src.utils.logging import get_pipeline_logger

# Set up logging
logger = get_pipeline_logger("dependency_injection_example")


# Define protocols for dependencies
class DataProvider(Protocol):
    """Protocol for a data provider dependency."""
    
    async def get_data(self) -> pl.DataFrame:
        """Get data from the source."""
        ...


class DataTransformer(Protocol):
    """Protocol for a data transformer dependency."""
    
    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Transform the provided data."""
        ...


class DataExporter(Protocol):
    """Protocol for a data exporter dependency."""
    
    async def export_data(self, df: pl.DataFrame) -> bool:
        """Export the provided data."""
        ...


# Implementations of the dependencies
class CSVDataProvider:
    """Provides data from a CSV file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    async def get_data(self) -> pl.DataFrame:
        """Get data from CSV (simulated)."""
        # In real code, this would read an actual CSV file
        logger.info(f"Reading CSV data from {self.file_path}")
        return pl.DataFrame({
            "player_id": [101, 102, 103, 104],
            "points": [12, 8, 15, 10],
            "assists": [5, 10, 7, 4],
            "source": ["CSV", "CSV", "CSV", "CSV"]
        })


class APIDataProvider:
    """Provides data from an API."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    async def get_data(self) -> pl.DataFrame:
        """Get data from API (simulated)."""
        # In real code, this would call an actual API
        logger.info(f"Fetching API data from {self.api_url}")
        return pl.DataFrame({
            "player_id": [201, 202, 203],
            "points": [22, 18, 25],
            "assists": [8, 12, 10],
            "source": ["API", "API", "API"]
        })


class BasicTransformer:
    """Basic data transformation."""
    
    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add a basic efficiency column."""
        logger.info("Applying basic transformation")
        return df.with_columns(
            (pl.col("points") + pl.col("assists")).alias("basic_score")
        )


class AdvancedTransformer:
    """Advanced data transformation."""
    
    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add weighted efficiency columns."""
        logger.info("Applying advanced transformation")
        return df.with_columns([
            (pl.col("points") * 1.0 + pl.col("assists") * 1.5).alias("weighted_score"),
            (pl.col("points") / (pl.col("points") + pl.col("assists")))
                .alias("scoring_ratio")
        ])


class ConsoleExporter:
    """Exports data to console."""
    
    async def export_data(self, df: pl.DataFrame) -> bool:
        """Print data to console."""
        logger.info("Exporting data to console")
        print("\nExported Data:")
        print(df)
        return True


class FileExporter:
    """Exports data to a file."""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
    
    async def export_data(self, df: pl.DataFrame) -> bool:
        """Export data to file (simulated)."""
        logger.info(f"Exporting data to file: {self.output_path}")
        # In a real implementation, this would write to a file
        print(f"\nWould export the following data to {self.output_path}:")
        print(df)
        return True


# Pipeline with injected dependencies
class AnalyticsPipeline(BasePipeline):
    """
    A pipeline that processes analytics data.
    
    This pipeline demonstrates dependency injection with multiple
    dependencies of different types.
    """
    
    @injectable
    def __init__(
        self,
        data_provider: DataProvider,
        transformer: DataTransformer,
        exporter: DataExporter
    ):
        """
        Initialize with dependencies.
        
        Args:
            data_provider: Source of input data
            transformer: Data transformation logic
            exporter: Output destination
        """
        super().__init__()
        self.data_provider = data_provider
        self.transformer = transformer
        self.exporter = exporter
    
    async def _validate(self, context: PipelineContext) -> bool:
        """This pipeline doesn't need additional validation."""
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute the analytics pipeline."""
        logger.info("Starting analytics pipeline execution")
        
        # Get data from provider
        try:
            input_df = await self.data_provider.get_data()
            logger.info(f"Received data with {len(input_df)} rows")
        except Exception as e:
            logger.error(f"Error getting data: {str(e)}")
            return PipelineResult(
                status=PipelineStatus.FAILURE,
                error=e,
                metadata={"error_stage": "data_provider"}
            )
        
        # Transform data
        try:
            transformed_df = self.transformer.transform(input_df)
            logger.info(f"Transformed data with {len(transformed_df)} rows")
        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            return PipelineResult(
                status=PipelineStatus.FAILURE,
                error=e,
                metadata={"error_stage": "transformer"}
            )
        
        # Export data
        try:
            export_success = await self.exporter.export_data(transformed_df)
            if not export_success:
                logger.warning("Exporter reported unsuccessful export")
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return PipelineResult(
                status=PipelineStatus.FAILURE,
                error=e,
                metadata={"error_stage": "exporter"}
            )
        
        # Return success result
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": transformed_df},
            metadata={
                "provider_type": self.data_provider.__class__.__name__,
                "transformer_type": self.transformer.__class__.__name__,
                "exporter_type": self.exporter.__class__.__name__,
                "row_count": len(transformed_df)
            }
        )
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        logger.debug("Cleaning up analytics pipeline")


async def run_example():
    """Run the dependency injection example."""
    print("\nDependency Injection Example")
    print("===========================")
    
    # Example 1: Creating a pipeline with explicit dependencies
    print("\n1. Creating a pipeline with explicit dependencies")
    
    # Create dependencies
    provider = CSVDataProvider(file_path="data/players.csv")
    transformer = BasicTransformer()
    exporter = ConsoleExporter()
    
    # Create and execute pipeline with explicit dependencies
    pipeline1 = AnalyticsPipeline(
        data_provider=provider,
        transformer=transformer,
        exporter=exporter
    )
    
    context = PipelineContext()
    result1 = await pipeline1.execute(context)
    
    print(f"\nResult status: {result1.status.name}")
    print("Metadata:")
    for key, value in result1.metadata.items():
        print(f"  {key}: {value}")
    
    # Example 2: Using registered dependencies
    print("\n\n2. Creating a pipeline with registered dependencies")
    
    # Clear any existing registrations
    Dependency.clear()
    
    # Register dependencies
    Dependency.register(DataProvider, APIDataProvider(
        api_url="https://api.example.com/stats",
        api_key="secret-key-123"
    ))
    Dependency.register(DataTransformer, AdvancedTransformer())
    Dependency.register(DataExporter, FileExporter(output_path="output/stats.csv"))
    
    # Create pipeline without explicitly providing dependencies
    # They will be injected from the registry
    pipeline2 = AnalyticsPipeline()
    
    result2 = await pipeline2.execute(context)
    
    print(f"\nResult status: {result2.status.name}")
    print("Metadata:")
    for key, value in result2.metadata.items():
        print(f"  {key}: {value}")
    
    # Clean up
    await pipeline1.cleanup()
    await pipeline2.cleanup()
    Dependency.clear()


if __name__ == "__main__":
    # Set up asyncio to run the example
    asyncio.run(run_example()) 