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
    
    def __init__(self, retry_enabled=False, max_retry_attempts=3):
        super().__init__(
            retry_enabled=retry_enabled,
            max_retry_attempts=max_retry_attempts
        )
        self.execute_called = False
        self.validate_called = False
        self.cleanup_called = False
        self.should_fail = False
        self.fail_count = 0  # Number of times to fail before succeeding
        self.validation_result = True
        self.execution_count = 0
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Mock implementation of execute."""
        self.execute_called = True
        self.execution_count += 1
        
        if self.should_fail:
            if self.execution_count <= self.fail_count:
                raise ValueError(f"Test execution failure (attempt {self.execution_count})")
            
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"test_output": pl.DataFrame({"result": [1, 2, 3]})},
            metadata={"execution_info": "test", "attempts": self.execution_count}
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
    
    @pytest.fixture
    def retry_pipeline(self):
        """Create a mock pipeline with retry enabled."""
        return MockPipeline(retry_enabled=True, max_retry_attempts=3)
    
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
        pipeline.fail_count = 1
        
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
        
    @pytest.mark.asyncio
    async def test_retry_successful_after_failures(self, retry_pipeline):
        """Test that retry functionality works with temporary failures."""
        # Set pipeline to fail initially but succeed after retries
        retry_pipeline.should_fail = True
        retry_pipeline.fail_count = 2  # Fail twice, succeed on third attempt
        
        # Create context and execute pipeline
        context = PipelineContext(params={"test": True})
        result = await retry_pipeline.execute(context)
        
        # Verify successful execution after retries
        assert retry_pipeline.execution_count > 1, "Should have multiple execution attempts"
        assert result.status == PipelineStatus.SUCCESS
        assert retry_pipeline.get_state().status == PipelineStatus.SUCCESS
        assert result.metadata["attempts"] == retry_pipeline.execution_count
        
    @pytest.mark.asyncio
    async def test_retry_exhausted_still_fails(self):
        """Test that retrying still fails if all attempts fail."""
        # Create pipeline that will always fail and has fewer retry attempts
        pipeline = MockPipeline(retry_enabled=True, max_retry_attempts=2)
        pipeline.should_fail = True
        pipeline.fail_count = 999  # Set to a high number to ensure all attempts fail
        
        # Create context and execute pipeline
        context = PipelineContext(params={"test": True})
        result = await pipeline.execute(context)
        
        # Verify failure after all retries exhausted
        assert pipeline.execution_count > 1, "Should have multiple execution attempts"
        assert result.status == PipelineStatus.FAILURE
        assert pipeline.get_state().status == PipelineStatus.FAILURE
        assert isinstance(result.error, ValueError) 