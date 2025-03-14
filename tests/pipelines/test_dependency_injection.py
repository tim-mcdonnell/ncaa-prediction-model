from typing import Protocol

import polars as pl
import pytest

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.dependency_injection import Dependency, injectable


# Define protocol for a dependency
class DataSource(Protocol):
    """Protocol for a data source dependency."""
    
    async def get_data(self) -> pl.DataFrame:
        """Get data from the source."""
        ...


# Real implementation
class SQLDataSource:
    """A data source that fetches from a SQL database."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    async def get_data(self) -> pl.DataFrame:
        """Simulate getting data from SQL."""
        # In a real implementation, this would query a database
        return pl.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30],
            "source": ["SQL", "SQL", "SQL"]
        })


# Mock implementation for testing
class MockDataSource:
    """A mock data source for testing."""
    
    async def get_data(self) -> pl.DataFrame:
        """Return test data."""
        return pl.DataFrame({
            "id": [1, 2, 3],
            "value": [100, 200, 300],
            "source": ["Mock", "Mock", "Mock"]
        })


# Pipeline that uses dependency injection
class DataSourcePipeline(BasePipeline):
    """A pipeline that uses a data source dependency."""
    
    @injectable
    def __init__(self, data_source: DataSource):
        """
        Initialize with a data source dependency.
        
        Args:
            data_source: The data source to use
        """
        super().__init__()
        self.data_source = data_source
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate the pipeline context."""
        # This pipeline doesn't need validation
        return True
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute by fetching data from the data source."""
        # Get data from the injected data source
        df = await self.data_source.get_data()
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": df},
            metadata={"source_type": self.data_source.__class__.__name__}
        )
        
    async def _cleanup(self) -> None:
        """Clean up resources."""
        pass


class TestDependencyInjection:
    """Tests for dependency injection in pipelines."""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_real_dependency(self):
        """Test pipeline with real dependency."""
        # Create pipeline with real dependency
        data_source = SQLDataSource(connection_string="postgresql://test:test@localhost/test")
        pipeline = DataSourcePipeline(data_source=data_source)
        
        # Execute pipeline
        context = PipelineContext()
        result = await pipeline.execute(context)
        
        # Verify result
        assert result.status == PipelineStatus.SUCCESS
        assert "result" in result.output_data
        df = result.output_data["result"]
        assert len(df) == 3
        assert df["source"][0] == "SQL"
        assert df["value"][0] == 10
    
    @pytest.mark.asyncio
    async def test_pipeline_with_mock_dependency(self):
        """Test pipeline with mock dependency."""
        # Create pipeline with mock dependency
        mock_source = MockDataSource()
        pipeline = DataSourcePipeline(data_source=mock_source)
        
        # Execute pipeline
        context = PipelineContext()
        result = await pipeline.execute(context)
        
        # Verify result with mock data
        assert result.status == PipelineStatus.SUCCESS
        assert "result" in result.output_data
        df = result.output_data["result"]
        assert len(df) == 3
        assert df["source"][0] == "Mock"
        assert df["value"][0] == 100
    
    @pytest.mark.asyncio
    async def test_dependency_registry(self):
        """Test registering and resolving dependencies."""
        # Register dependency
        Dependency.register(DataSource, MockDataSource())
        
        # Create pipeline without explicitly providing dependency
        pipeline = DataSourcePipeline()
        
        # Execute pipeline - should use registered dependency
        context = PipelineContext()
        result = await pipeline.execute(context)
        
        # Verify result uses registered mock
        assert result.status == PipelineStatus.SUCCESS
        df = result.output_data["result"]
        assert df["source"][0] == "Mock"
        
        # Clean up registry for other tests
        Dependency.clear()
    
    @pytest.mark.asyncio
    async def test_override_registered_dependency(self):
        """Test explicitly providing dependency overrides registry."""
        # Register one dependency
        Dependency.register(DataSource, SQLDataSource(connection_string="unused"))
        
        # But explicitly provide a different one
        mock_source = MockDataSource()
        pipeline = DataSourcePipeline(data_source=mock_source)
        
        # Execute pipeline - should use explicitly provided dependency
        context = PipelineContext()
        result = await pipeline.execute(context)
        
        # Verify result
        assert result.status == PipelineStatus.SUCCESS
        df = result.output_data["result"]
        assert df["source"][0] == "Mock"  # Using explicit, not registered
        
        # Clean up registry for other tests
        Dependency.clear() 