import asyncio
from typing import List

import pytest

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.monitoring import MonitoringEvent, PipelineMonitor, register_monitor


# Mock monitor for testing that collects events
class MockMonitor(PipelineMonitor):
    """Mock monitor that records all events for testing."""
    
    def __init__(self):
        self.events: List[MonitoringEvent] = []
        
    async def record_event(self, event: MonitoringEvent) -> None:
        """Record an event by adding it to the list."""
        self.events.append(event)


# Simple test pipeline
class SimpleTestPipeline(BasePipeline):
    """A simple pipeline for testing monitoring."""
    
    def __init__(self, fail: bool = False, slow: bool = False):
        super().__init__()
        self.fail = fail
        self.slow = slow
        
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate the pipeline context."""
        return not self.fail
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute the pipeline."""
        if self.slow:
            await asyncio.sleep(0.1)  # Simulate slow execution
            
        if self.fail:
            raise ValueError("Test failure")
            
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": "test_data"},
            metadata={"test": True}
        )
        
    async def _cleanup(self) -> None:
        """Clean up resources."""
        pass


class TestMonitoringHooks:
    """Tests for pipeline monitoring hooks."""
    
    @pytest.fixture
    def monitor(self):
        """Create a mock monitor."""
        return MockMonitor()
    
    @pytest.fixture
    def register_test_monitor(self, monitor):
        """Register the test monitor."""
        register_monitor(monitor)
        yield
        # Clean up - unregister all monitors
        from src.pipelines.monitoring import _monitors
        _monitors.clear()
    
    @pytest.mark.asyncio
    async def test_pipeline_success_monitoring(self, monitor, register_test_monitor):
        """Test that successful pipeline execution is monitored."""
        # Create and execute pipeline
        pipeline = SimpleTestPipeline()
        context = PipelineContext(params={"test": True})
        result = await pipeline.execute(context)
        
        # Verify execution
        assert result.status == PipelineStatus.SUCCESS
        
        # Check that events were recorded
        assert len(monitor.events) >= 3  # At least start, success, end events
        
        # Check for specific events
        event_types = [event.event_type for event in monitor.events]
        assert "pipeline_start" in event_types
        assert "pipeline_success" in event_types
        assert "pipeline_end" in event_types
        
        # Check event data
        start_event = next(e for e in monitor.events if e.event_type == "pipeline_start")
        assert start_event.pipeline_name == "SimpleTestPipeline"
        assert start_event.data["context_params"] == {"test": True}
    
    @pytest.mark.asyncio
    async def test_pipeline_failure_monitoring(self, monitor, register_test_monitor):
        """Test that failed pipeline execution is monitored."""
        # Create and execute failing pipeline
        pipeline = SimpleTestPipeline(fail=True)
        context = PipelineContext()
        
        # Execute - no need to catch exceptions as validation failures don't throw
        result = await pipeline.execute(context)
        
        # Verify status is failure
        assert result.status == PipelineStatus.VALIDATION_FAILURE
        
        # Check that events were recorded
        assert len(monitor.events) >= 3  # At least start, error, end events
        
        # Check for specific events
        event_types = [event.event_type for event in monitor.events]
        assert "pipeline_start" in event_types
        assert "pipeline_error" in event_types
        assert "pipeline_end" in event_types
        
        # Check error event
        error_event = next(e for e in monitor.events if e.event_type == "pipeline_error")
        assert error_event.pipeline_name == "SimpleTestPipeline"
        assert "error_type" in error_event.data
        assert "ValidationFailure" in error_event.data["error_type"]
    
    @pytest.mark.asyncio
    async def test_pipeline_timing_monitoring(self, monitor, register_test_monitor):
        """Test that pipeline timing is monitored."""
        # Create and execute slow pipeline
        pipeline = SimpleTestPipeline(slow=True)
        context = PipelineContext()
        # We need the result for execution, but don't use it in assertions
        await pipeline.execute(context)
        
        # Check timing events
        end_event = next(e for e in monitor.events if e.event_type == "pipeline_end")
        assert "execution_time_ms" in end_event.data
        assert end_event.data["execution_time_ms"] > 0
        
        # Slow pipeline should take at least 100ms
        assert end_event.data["execution_time_ms"] >= 100
    
    @pytest.mark.asyncio
    async def test_multiple_monitors(self, monitor):
        """Test that multiple monitors can be registered."""
        # Create two monitors
        monitor1 = MockMonitor()
        monitor2 = MockMonitor()
        
        # Register both
        register_monitor(monitor1)
        register_monitor(monitor2)
        
        # Execute pipeline
        pipeline = SimpleTestPipeline()
        context = PipelineContext()
        # We need the result for execution, but don't use it in assertions
        await pipeline.execute(context)
        
        # Verify both monitors recorded events
        assert len(monitor1.events) > 0
        assert len(monitor2.events) > 0
        
        # Verify the same events were recorded
        assert len(monitor1.events) == len(monitor2.events)
        
        # Clean up
        from src.pipelines.monitoring import _monitors
        _monitors.clear() 