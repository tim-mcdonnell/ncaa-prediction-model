import polars as pl
import pytest

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)


class TestPipelineContext:
    """Tests for the PipelineContext class."""
    
    def test_pipeline_context_creation(self):
        """Test that a pipeline context can be created with parameters."""
        # Create context with parameters
        context = PipelineContext(
            params={"param1": "value1", "param2": 123},
            input_data={"data1": pl.DataFrame({"col1": [1, 2, 3]})}
        )
        
        # Verify the context properties
        assert context.params["param1"] == "value1"
        assert context.params["param2"] == 123
        assert isinstance(context.input_data["data1"], pl.DataFrame)
        assert context.input_data["data1"].shape == (3, 1)
        
    def test_pipeline_context_defaults(self):
        """Test that a pipeline context can be created with default values."""
        # Create context with no parameters
        context = PipelineContext()
        
        # Verify default values
        assert context.params == {}
        assert context.input_data == {}
        assert context.start_time is not None


class TestPipelineResult:
    """Tests for the PipelineResult class."""
    
    def test_pipeline_result_creation(self):
        """Test that a pipeline result can be created with data."""
        # Create result with output data
        result = PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result1": pl.DataFrame({"col1": [1, 2, 3]})},
            metadata={"processing_time": 1.5}
        )
        
        # Verify result properties
        assert result.status == PipelineStatus.SUCCESS
        assert isinstance(result.output_data["result1"], pl.DataFrame)
        assert result.metadata["processing_time"] == 1.5
        
    def test_pipeline_result_failure(self):
        """Test that a pipeline result can represent failure."""
        # Create a failure result
        error = ValueError("Test error")
        result = PipelineResult(
            status=PipelineStatus.FAILURE,
            error=error,
            metadata={"error_type": "ValueError"}
        )
        
        # Verify failure properties
        assert result.status == PipelineStatus.FAILURE
        assert result.error == error
        assert result.metadata["error_type"] == "ValueError"
        assert result.output_data == {}


class MockPipeline(BasePipeline):
    """Mock implementation of BasePipeline for testing."""
    
    def __init__(self):
        super().__init__()
        self.execute_called = False
        self.validate_called = False
        self.cleanup_called = False
        self.should_fail = False
        self.validation_result = True
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Mock implementation of execute."""
        self.execute_called = True
        
        if self.should_fail:
            raise ValueError("Test execution failure")
            
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"test_output": pl.DataFrame({"result": [1, 2, 3]})},
            metadata={"execution_info": "test"}
        )
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Mock implementation of validate."""
        self.validate_called = True
        return self.validation_result
        
    async def _cleanup(self) -> None:
        """Mock implementation of cleanup."""
        self.cleanup_called = True


class TestBasePipeline:
    """Tests for the BasePipeline abstract class."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a mock pipeline instance for testing."""
        return MockPipeline()
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_success(self, pipeline):
        """Test successful pipeline execution."""
        # Create context and execute pipeline
        context = PipelineContext(params={"test": True})
        result = await pipeline.execute(context)
        
        # Verify execution
        assert pipeline.execute_called
        assert pipeline.validate_called
        assert result.status == PipelineStatus.SUCCESS
        assert pipeline.get_state().status == PipelineStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_failure(self, pipeline):
        """Test pipeline execution failure."""
        # Set pipeline to fail
        pipeline.should_fail = True
        
        # Create context and execute pipeline
        context = PipelineContext(params={"test": True})
        result = await pipeline.execute(context)
        
        # Verify failure
        assert pipeline.execute_called
        assert pipeline.validate_called
        assert result.status == PipelineStatus.FAILURE
        assert isinstance(result.error, ValueError)
        assert pipeline.get_state().status == PipelineStatus.FAILURE
    
    @pytest.mark.asyncio
    async def test_pipeline_validation_failure(self, pipeline):
        """Test pipeline validation failure."""
        # Set validation to fail
        pipeline.validation_result = False
        
        # Create context and execute pipeline
        context = PipelineContext(params={"test": True})
        result = await pipeline.execute(context)
        
        # Verify validation failure
        assert not pipeline.execute_called
        assert pipeline.validate_called
        assert result.status == PipelineStatus.VALIDATION_FAILURE
        assert pipeline.get_state().status == PipelineStatus.VALIDATION_FAILURE
    
    @pytest.mark.asyncio
    async def test_pipeline_cleanup(self, pipeline):
        """Test pipeline cleanup."""
        # Execute and then cleanup
        context = PipelineContext(params={"test": True})
        await pipeline.execute(context)
        await pipeline.cleanup()
        
        # Verify cleanup was called
        assert pipeline.cleanup_called
    
    @pytest.mark.asyncio
    async def test_pipeline_state(self, pipeline):
        """Test pipeline state tracking."""
        # Check initial state
        assert pipeline.get_state().status == PipelineStatus.NOT_STARTED
        
        # Execute pipeline
        context = PipelineContext(params={"test": True})
        await pipeline.execute(context)
        
        # Verify state after execution
        state = pipeline.get_state()
        assert state.status == PipelineStatus.SUCCESS
        assert state.start_time is not None
        assert state.end_time is not None
        assert state.execution_time > 0 