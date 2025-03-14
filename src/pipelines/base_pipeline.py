"""
Base Pipeline Framework

This module defines the core pipeline infrastructure for the NCAA prediction model.
It provides a foundation for all pipeline components with shared functionality for:
- Pipeline execution and lifecycle management
- State tracking and persistence
- Error handling and logging
- Configuration management
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

import polars as pl

from src.utils.resilience.retry import retry

# Set up logging
logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Possible states for a pipeline."""
    NOT_STARTED = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    VALIDATION_FAILURE = auto()
    CANCELED = auto()


class PipelineContext:
    """
    Execution context for a pipeline.
    
    Contains all input parameters, data, and configuration needed
    for pipeline execution.
    
    Attributes:
        params: Dictionary of pipeline parameters
        input_data: Dictionary of input data (e.g., DataFrames, models)
        start_time: When the context was created
    """
    
    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new pipeline context.
        
        Args:
            params: Dictionary of pipeline parameters
            input_data: Dictionary of input data (e.g., DataFrames, models)
        """
        self.params = params or {}
        self.input_data = input_data or {}
        self.start_time = datetime.now()


class PipelineResult:
    """
    Result of a pipeline execution.
    
    Contains the execution status, output data, and additional metadata.
    
    Attributes:
        status: Status of the pipeline execution
        output_data: Dictionary of output data (e.g., DataFrames)
        metadata: Additional information about the execution
        error: Exception that caused failure (if any)
    """
    
    def __init__(
        self,
        status: PipelineStatus,
        output_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """
        Initialize a new pipeline result.
        
        Args:
            status: Status of the pipeline execution
            output_data: Dictionary of output data (e.g., DataFrames)
            metadata: Additional information about the execution
            error: Exception that caused failure (if any)
        """
        self.status = status
        self.output_data = output_data or {}
        self.metadata = metadata or {}
        self.error = error


class PipelineState:
    """
    State information for a pipeline.
    
    Tracks the current status and timing of pipeline execution.
    
    Attributes:
        status: Current pipeline status
        start_time: When the pipeline started executing
        end_time: When the pipeline finished executing
        execution_time: Total execution time in seconds
        error: Exception that caused failure (if any)
    """
    
    def __init__(self):
        """Initialize a new pipeline state."""
        self.status = PipelineStatus.NOT_STARTED
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.execution_time: Optional[float] = None
        self.error: Optional[Exception] = None


class BasePipeline(ABC):
    """
    Abstract base class for all pipeline components.
    
    Provides shared functionality for pipeline execution, validation,
    error handling, and state management.
    
    This class should be extended by concrete pipeline implementations.
    """
    
    def __init__(self):
        """Initialize a new base pipeline."""
        self._state = PipelineState()
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    async def execute(self, context: PipelineContext) -> PipelineResult:
        """
        Execute the pipeline with the given context.
        
        This method handles the overall execution flow, including:
        - Validating inputs
        - Tracking state and timing
        - Error handling
        - Logging
        
        Args:
            context: Execution context with parameters and input data
            
        Returns:
            Result of the pipeline execution
        """
        # Update state to running
        self._state.status = PipelineStatus.RUNNING
        self._state.start_time = datetime.now()
        logger.info(f"Starting execution of {self.__class__.__name__}")
        
        start_time = time.time()
        
        try:
            # First validate the pipeline context
            is_valid = await self._validate(context)
            if not is_valid:
                logger.error(f"Validation failed for {self.__class__.__name__}")
                self._state.status = PipelineStatus.VALIDATION_FAILURE
                return PipelineResult(
                    status=PipelineStatus.VALIDATION_FAILURE,
                    metadata={"validation_error": "Pipeline validation failed"}
                )
            
            # Execute the pipeline implementation
            logger.debug(f"Executing {self.__class__.__name__}")
            result = await self._execute(context)
            self._state.status = result.status
            
            logger.info(f"Execution of {self.__class__.__name__} completed with status: {result.status.name}")
            return result
            
        except Exception as e:
            logger.exception(f"Error executing {self.__class__.__name__}: {str(e)}")
            self._state.status = PipelineStatus.FAILURE
            self._state.error = e
            
            return PipelineResult(
                status=PipelineStatus.FAILURE,
                error=e,
                metadata={"error_type": e.__class__.__name__, "error_msg": str(e)}
            )
            
        finally:
            # Update state with timing information
            self._state.end_time = datetime.now()
            self._state.execution_time = time.time() - start_time
            logger.debug(
                f"Execution of {self.__class__.__name__} took "
                f"{self._state.execution_time:.2f} seconds"
            )
    
    @abstractmethod
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """
        Implement the core pipeline logic.
        
        This abstract method should be implemented by subclasses to
        provide the actual pipeline functionality.
        
        Args:
            context: Execution context with parameters and input data
            
        Returns:
            Result of the pipeline execution
        """
        pass
    
    @abstractmethod
    async def _validate(self, context: PipelineContext) -> bool:
        """
        Validate the pipeline context before execution.
        
        This abstract method should be implemented by subclasses to
        check that the provided context is valid for this pipeline.
        
        Args:
            context: Execution context to validate
            
        Returns:
            True if the context is valid, False otherwise
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up resources after pipeline execution.
        
        This method handles resource cleanup after pipeline execution,
        delegating to the _cleanup implementation.
        
        Returns:
            None
        """
        logger.debug(f"Cleaning up resources for {self.__class__.__name__}")
        try:
            await self._cleanup()
            logger.debug(f"Cleanup completed for {self.__class__.__name__}")
        except Exception as e:
            logger.exception(f"Error during cleanup of {self.__class__.__name__}: {str(e)}")
    
    @abstractmethod
    async def _cleanup(self) -> None:
        """
        Implement resource cleanup logic.
        
        This abstract method should be implemented by subclasses to
        clean up any resources used during pipeline execution.
        
        Returns:
            None
        """
        pass
    
    def get_state(self) -> PipelineState:
        """
        Get the current pipeline state.
        
        Returns:
            Current state of the pipeline
        """
        return self._state
