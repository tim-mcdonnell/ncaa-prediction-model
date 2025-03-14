"""
Pipeline Monitoring Example

This example demonstrates how to use monitoring hooks with
pipelines to collect telemetry and metrics.
"""

import asyncio
from typing import Any, Dict, List

import polars as pl

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)
from src.pipelines.monitoring import (
    ConsoleMonitor,
    MonitoringEvent,
    PipelineMonitor,
    register_monitor,
)
from src.utils.logging import get_pipeline_logger

# Set up logging
logger = get_pipeline_logger("monitoring_example")


# Custom monitor that collects detailed statistics
class StatsMonitor(PipelineMonitor):
    """A monitor that collects statistics from pipeline executions."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.events: List[MonitoringEvent] = []
        self.stats: Dict[str, Any] = {
            "pipelines_executed": 0,
            "pipelines_succeeded": 0,
            "pipelines_failed": 0,
            "total_execution_time_ms": 0,
            "executions_by_pipeline": {}
        }
    
    async def record_event(self, event: MonitoringEvent) -> None:
        """Record an event and update statistics."""
        # Store the event
        self.events.append(event)
        
        # Update statistics based on event type
        if event.event_type == "pipeline_start":
            # A new pipeline execution has started
            if event.pipeline_name not in self.stats["executions_by_pipeline"]:
                self.stats["executions_by_pipeline"][event.pipeline_name] = {
                    "count": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_time_ms": 0,
                    "avg_time_ms": 0
                }
                
            # Increment execution count
            self.stats["pipelines_executed"] += 1
            self.stats["executions_by_pipeline"][event.pipeline_name]["count"] += 1
            
        elif event.event_type == "pipeline_success":
            # A pipeline has succeeded
            self.stats["pipelines_succeeded"] += 1
            self.stats["executions_by_pipeline"][event.pipeline_name]["successes"] += 1
            
        elif event.event_type == "pipeline_error":
            # A pipeline has failed
            self.stats["pipelines_failed"] += 1
            self.stats["executions_by_pipeline"][event.pipeline_name]["failures"] += 1
            
        elif event.event_type == "pipeline_end":
            # A pipeline has finished (update timing)
            time_ms = event.data.get("execution_time_ms", 0)
            self.stats["total_execution_time_ms"] += time_ms
            
            pipeline_stats = self.stats["executions_by_pipeline"][event.pipeline_name]
            pipeline_stats["total_time_ms"] += time_ms
            pipeline_stats["avg_time_ms"] = (
                pipeline_stats["total_time_ms"] / pipeline_stats["count"]
            )
    
    def print_report(self) -> None:
        """Print a statistical report."""
        print("\n===== Pipeline Execution Statistics =====")
        print(f"Pipelines Executed: {self.stats['pipelines_executed']}")
        print(f"Successful: {self.stats['pipelines_succeeded']}")
        print(f"Failed: {self.stats['pipelines_failed']}")
        
        if self.stats['pipelines_executed'] > 0:
            total_ms = self.stats['total_execution_time_ms']
            count = self.stats['pipelines_executed']
            avg_time = total_ms / count
            print(f"Average Execution Time: {avg_time:.2f}ms")
        
        print("\nBy Pipeline Type:")
        for pipeline_name, stats in self.stats["executions_by_pipeline"].items():
            print(f"  {pipeline_name}:")
            print(f"    Executions: {stats['count']}")
            success_rate = (stats['successes'] / stats['count']) * 100
            print(f"    Success Rate: {success_rate:.1f}%")
            print(f"    Average Time: {stats['avg_time_ms']:.2f}ms")


# Example pipelines to monitor
class DataLoadPipeline(BasePipeline):
    """Pipeline that loads data."""
    
    def __init__(self, fail: bool = False, delay: float = 0.0):
        """
        Initialize the data load pipeline.
        
        Args:
            fail: Whether to simulate a failure
            delay: How long to delay execution (in seconds)
        """
        super().__init__()
        self.fail = fail
        self.delay = delay
    
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate the pipeline context."""
        return not self.fail
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute the data load pipeline."""
        logger.info("Loading data")
        
        # Simulate work with delay
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        # Create sample data
        df = pl.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "value": [10, 20, 30, 40, 50]
        })
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"data": df},
            metadata={"row_count": len(df)}
        )
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        pass


class DataProcessPipeline(BasePipeline):
    """Pipeline that processes data."""
    
    def __init__(self, operation: str = "double", delay: float = 0.0):
        """
        Initialize the data process pipeline.
        
        Args:
            operation: Operation to perform (double, square, etc.)
            delay: How long to delay execution (in seconds)
        """
        super().__init__()
        self.operation = operation
        self.delay = delay
    
    async def _validate(self, context: PipelineContext) -> bool:
        """Validate the pipeline context."""
        if "data" not in context.input_data:
            logger.error("Missing required input data")
            return False
            
        if not isinstance(context.input_data["data"], pl.DataFrame):
            logger.error("Input data must be a DataFrame")
            return False
            
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """Execute the data process pipeline."""
        logger.info(f"Processing data with operation: {self.operation}")
        
        # Simulate work with delay
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        # Get input data
        df = context.input_data["data"]
        
        # Apply operation
        if self.operation == "double":
            result_df = df.with_columns(pl.col("value") * 2)
        elif self.operation == "square":
            result_df = df.with_columns(pl.col("value") ** 2)
        else:
            result_df = df  # No operation
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_df},
            metadata={
                "operation": self.operation,
                "row_count": len(result_df)
            }
        )
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        pass


async def run_example():
    """Run the monitoring example."""
    print("\nPipeline Monitoring Example")
    print("=========================")
    
    # Create and register monitors
    console_monitor = ConsoleMonitor()
    stats_monitor = StatsMonitor()
    
    register_monitor(console_monitor)
    register_monitor(stats_monitor)
    
    print("\n1. Running successful pipelines")
    
    # Run a successful data load pipeline
    load_pipeline = DataLoadPipeline(delay=0.1)
    load_context = PipelineContext()
    load_result = await load_pipeline.execute(load_context)
    
    # Run a successful data process pipeline
    process_pipeline = DataProcessPipeline(operation="double", delay=0.2)
    data_from_load = load_result.output_data["data"]
    process_context = PipelineContext(input_data={"data": data_from_load})
    # Execute pipeline but we don't need to store the result
    await process_pipeline.execute(process_context)
    
    print("\n2. Running a failing pipeline")
    
    # Run a failing pipeline to demonstrate error monitoring
    failing_pipeline = DataLoadPipeline(fail=True)
    failing_context = PipelineContext()
    # Execute pipeline but we don't need to store the result
    await failing_pipeline.execute(failing_context)
    
    print("\n3. Running different operation types")
    
    # Run with different operation
    square_pipeline = DataProcessPipeline(operation="square", delay=0.15)
    data_from_load = load_result.output_data["data"]
    square_context = PipelineContext(input_data={"data": data_from_load})
    # Execute pipeline but we don't need to store the result
    await square_pipeline.execute(square_context)
    
    # Print the statistics report
    stats_monitor.print_report()


if __name__ == "__main__":
    # Set up asyncio to run the example
    asyncio.run(run_example()) 