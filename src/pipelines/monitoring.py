# Base Pipeline Framework - Monitoring Component
"""
Monitoring hooks for the base pipeline framework.

This module provides event-based monitoring for pipeline execution.
"""

import abc
import asyncio
import json
import logging
import time
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

# Circular import handled specially - importing here to avoid dependency cycle issues
from src.pipelines.base_pipeline import BasePipeline

# Set up logging
logger = logging.getLogger(__name__)

# Global registry of monitors
_monitors: List["PipelineMonitor"] = []


@dataclass
class MonitoringEvent:
    """
    Represents a monitoring event from a pipeline.
    
    Attributes:
        event_type: Type of event (e.g., start, end, error)
        pipeline_name: Name of the pipeline generating the event
        timestamp: When the event occurred
        data: Additional event data
    """
    event_type: str
    pipeline_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class PipelineMonitor(ABC):
    """
    Abstract base class for pipeline monitors.
    
    Monitors receive events from pipelines and can process them
    as needed (e.g., store in a database, send to metrics system).
    """
    
    @abc.abstractmethod
    async def record_event(self, event: MonitoringEvent) -> None:
        """
        Record a monitoring event.
        
        Args:
            event: The event to record
        """
        pass


class ConsoleMonitor(PipelineMonitor):
    """
    A simple monitor that logs events to the console.
    
    This is useful for development and debugging.
    """
    
    async def record_event(self, event: MonitoringEvent) -> None:
        """Log the event to the console."""
        logger.info(
            f"Pipeline event: {event.event_type} | {event.pipeline_name} | "
            f"{event.timestamp.isoformat()} | {json.dumps(event.data)}"
        )


def register_monitor(monitor: PipelineMonitor) -> None:
    """
    Register a monitor to receive pipeline events.
    
    Args:
        monitor: The monitor to register
    """
    _monitors.append(monitor)
    logger.debug(f"Registered monitor: {monitor.__class__.__name__}")


async def broadcast_event(event: MonitoringEvent) -> None:
    """
    Broadcast an event to all registered monitors.
    
    Args:
        event: The event to broadcast
    """
    tasks = []
    for monitor in _monitors:
        try:
            tasks.append(monitor.record_event(event))
        except Exception as e:
            monitor_name = monitor.__class__.__name__
            error_msg = str(e)
            logger.error(f"Error sending event to monitor {monitor_name}: {error_msg}")
    
    if tasks:
        await asyncio.gather(*tasks)


# Patch BasePipeline.execute to add monitoring
# Store the original method
_original_execute = BasePipeline.execute


# Define new execute method with monitoring
async def _monitored_execute(self, context):
    """Execute with monitoring."""
    # Start event
    start_time = time.time()
    await broadcast_event(MonitoringEvent(
        event_type="pipeline_start",
        pipeline_name=self.__class__.__name__,
        data={
            "context_params": context.params
        }
    ))
    
    try:
        # Execute the pipeline
        result = await _original_execute(self, context)
        
        # Check result status
        if result.status == result.status.SUCCESS:
            # Success event
            await broadcast_event(MonitoringEvent(
                event_type="pipeline_success",
                pipeline_name=self.__class__.__name__,
                data={
                    "status": result.status.name,
                    "metadata": result.metadata
                }
            ))
        else:
            # Failure event (validation or other non-exception failure)
            await broadcast_event(MonitoringEvent(
                event_type="pipeline_error",
                pipeline_name=self.__class__.__name__,
                data={
                    "status": result.status.name,
                    "error_type": ("ValidationFailure" 
                                  if result.status == result.status.VALIDATION_FAILURE 
                                  else "ExecutionFailure"),
                    "metadata": result.metadata
                }
            ))
        
        return result
        
    except Exception as e:
        # Exception event
        await broadcast_event(MonitoringEvent(
            event_type="pipeline_error",
            pipeline_name=self.__class__.__name__,
            data={
                "error_type": e.__class__.__name__,
                "error_message": str(e)
            }
        ))
        
        # Re-raise the exception
        raise
        
    finally:
        # End event (always sent)
        execution_time_ms = int((time.time() - start_time) * 1000)
        await broadcast_event(MonitoringEvent(
            event_type="pipeline_end",
            pipeline_name=self.__class__.__name__,
            data={
                "execution_time_ms": execution_time_ms
            }
        ))


# Replace the method
BasePipeline.execute = _monitored_execute 