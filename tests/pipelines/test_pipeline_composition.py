import polars as pl
import pytest

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.pipeline_composition import ComposedPipeline


class SimpleTestPipeline(BasePipeline):
    """A simple test pipeline that transforms data."""
    
    def __init__(self, name, transform_fn=None):
        super().__init__()
        self.name = name
        self.transform_fn = transform_fn or (lambda df: df)
    
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate the pipeline context."""
        return "data" in context.input_data
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute the pipeline by applying the transform function."""
        input_df = context.input_data["data"]
        result_df = self.transform_fn(input_df)
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={"pipeline_name": self.name}
        )
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        pass


class TestPipelineComposition:
    """Tests for pipeline composition functionality."""
    
    @pytest.fixture
    def first_pipeline(self):
        """Create the first pipeline in the composition."""
        return SimpleTestPipeline(
            "first",
            lambda df: df.with_columns(pl.col("value") * 2)
        )
    
    @pytest.fixture
    def second_pipeline(self):
        """Create the second pipeline in the composition."""
        return SimpleTestPipeline(
            "second",
            lambda df: df.with_columns(pl.col("value") + 10)
        )
    
    @pytest.mark.asyncio
    async def test_pipeline_composition_creation(self, first_pipeline, second_pipeline):
        """Test that a composed pipeline can be created."""
        # Create a composed pipeline
        composed = ComposedPipeline(
            name="composed_pipeline",
            pipelines=[first_pipeline, second_pipeline]
        )
        
        # Verify properties
        assert composed.name == "composed_pipeline"
        assert len(composed.pipelines) == 2
        assert composed.pipelines[0] == first_pipeline
        assert composed.pipelines[1] == second_pipeline
    
    @pytest.mark.asyncio
    async def test_composed_pipeline_execution(self, first_pipeline, second_pipeline):
        """Test execution of a composed pipeline."""
        # Create test data
        input_df = pl.DataFrame({
            "id": [1, 2, 3],
            "value": [5, 10, 15]
        })
        
        # Create a composed pipeline
        composed = ComposedPipeline(
            name="composed_pipeline",
            pipelines=[first_pipeline, second_pipeline]
        )
        
        # Execute the composed pipeline
        context = PipelineContext(input_data={"data": input_df})
        result = await composed.execute(context)
        
        # Verify results
        assert result.status == PipelineStatus.SUCCESS
        
        # Check that both transformations were applied
        # First: value * 2, Second: (value * a) + 10
        expected_values = [20, 30, 40]  # (5*2)+10, (10*2)+10, (15*2)+10
        result_df = result.output_data["result"]
        assert result_df["value"].to_list() == expected_values
    
    @pytest.mark.asyncio
    async def test_composed_pipeline_early_failure(self, first_pipeline):
        """Test that a composed pipeline handles failure in any component."""
        # Create a failing pipeline
        failing_pipeline = SimpleTestPipeline("failing")
        
        # Override _execute to make it fail
        async def failing_execute(self, context):
            raise ValueError("Test failure")
        
        failing_pipeline._execute = failing_execute.__get__(failing_pipeline)
        
        # Create a composed pipeline with the failing pipeline
        composed = ComposedPipeline(
            name="failing_composed",
            pipelines=[first_pipeline, failing_pipeline]
        )
        
        # Execute the composed pipeline
        input_df = pl.DataFrame({"id": [1], "value": [5]})
        context = PipelineContext(input_data={"data": input_df})
        result = await composed.execute(context)
        
        # Verify that the overall pipeline failed
        assert result.status == PipelineStatus.FAILURE
        assert isinstance(result.error, ValueError)
    
    @pytest.mark.asyncio
    async def test_composed_pipeline_cleanup(self, first_pipeline, second_pipeline):
        """Test that cleanup is called on all component pipelines."""
        # Track cleanup calls
        cleanup_calls = []
        
        # Override _cleanup to track calls
        async def tracked_cleanup_first(self):
            cleanup_calls.append("first")
        
        async def tracked_cleanup_second(self):
            cleanup_calls.append("second")
        
        first_pipeline._cleanup = tracked_cleanup_first.__get__(first_pipeline)
        second_pipeline._cleanup = tracked_cleanup_second.__get__(second_pipeline)
        
        # Create a composed pipeline
        composed = ComposedPipeline(
            name="cleanup_test",
            pipelines=[first_pipeline, second_pipeline]
        )
        
        # Execute and then cleanup
        input_df = pl.DataFrame({"id": [1], "value": [5]})
        context = PipelineContext(input_data={"data": input_df})
        await composed.execute(context)
        await composed.cleanup()
        
        # Verify both cleanups were called
        assert len(cleanup_calls) == 2
        assert "first" in cleanup_calls
        assert "second" in cleanup_calls 