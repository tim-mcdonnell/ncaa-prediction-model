"""
Pipeline Composition

This module provides functionality for composing multiple pipelines 
into a single pipeline for sequential execution.
"""

import logging
from typing import List

from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)

# Set up logging
logger = logging.getLogger(__name__)


class ComposedPipeline(BasePipeline):
    """
    A pipeline that composes multiple other pipelines for sequential execution.
    
    Each pipeline in the sequence receives the output of the previous pipeline
    as its input. This allows for creating complex data processing flows from
    simple building blocks.
    
    Attributes:
        name: Name of the composed pipeline
        pipelines: List of pipelines to execute in sequence
    """
    
    def __init__(self, name: str, pipelines: List[BasePipeline]):
        """
        Initialize a composed pipeline.
        
        Args:
            name: Name of the composed pipeline
            pipelines: List of pipelines to execute in sequence
        """
        super().__init__()
        self.name = name
        self.pipelines = pipelines
        pipes_count = len(pipelines)
        logger.debug(
            f"Initialized ComposedPipeline '{name}' with "
            f"{pipes_count} components"
        )
    
    async def _validate(self, context: PipelineContext) -> bool:
        """
        Validate the first pipeline with the given context.
        
        For composed pipelines, we only validate the first pipeline with the 
        initial context. Subsequent pipelines will be validated with their 
        actual input context at execution time.
        
        Args:
            context: The pipeline context to validate
            
        Returns:
            Whether the pipeline is valid with the given context
        """
        logger.debug(f"Validating composed pipeline '{self.name}'")
        
        # Only validate the first pipeline with the initial context
        # The other pipelines will be validated during execution
        if not self.pipelines:
            logger.error(f"Composed pipeline '{self.name}' has no component pipelines")
            return False
            
        pipeline_valid = await self.pipelines[0]._validate(context)
        if not pipeline_valid:
            logger.error(f"Validation failed for first component in '{self.name}'")
            return False
        
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """
        Execute all component pipelines in sequence.
        
        Each pipeline receives the output of the previous pipeline as its input.
        Validation for pipelines after the first one happens during execution.
        
        Args:
            context: Execution context
            
        Returns:
            Result of the final pipeline in the sequence
        """
        logger.info(f"Executing composed pipeline '{self.name}'")
        
        # Start with the original context
        current_context = context
        
        # Execute each pipeline in sequence
        for i, pipeline in enumerate(self.pipelines):
            logger.debug(f"Executing component {i} in '{self.name}'")
            
            try:
                # Validate with actual context (except first pipeline)
                if i > 0:
                    pipeline_valid = await pipeline._validate(current_context)
                    if not pipeline_valid:
                        logger.error(
                            f"Validation failed for component {i} in '{self.name}'"
                        )
                        return PipelineResult(
                            status=PipelineStatus.VALIDATION_FAILURE,
                            metadata={
                                "validation_error": 
                                    f"Pipeline validation failed for component {i}",
                                "component_name": pipeline.__class__.__name__
                            }
                        )
                
                # Execute the current pipeline
                result = await pipeline.execute(current_context)
                
                # Check if execution was successful
                if result.status != PipelineStatus.SUCCESS:
                    logger.error(
                        f"Component {i} in '{self.name}' failed with status: "
                        f"{result.status.name}"
                    )
                    return result
                
                # Prepare context for next pipeline
                if i < len(self.pipelines) - 1:
                    # Create a new context with the output of this pipeline
                    current_context = PipelineContext(
                        params=context.params,
                        input_data={"data": result.output_data["result"]}
                    )
            
            except Exception as e:
                logger.exception(f"Error in component {i} of '{self.name}': {str(e)}")
                return PipelineResult(
                    status=PipelineStatus.FAILURE,
                    error=e,
                    metadata={
                        "component_index": i,
                        "component_name": pipeline.__class__.__name__,
                        "error_type": e.__class__.__name__,
                        "error_msg": str(e)
                    }
                )
        
        # Return the result of the final pipeline
        return result
    
    async def _cleanup(self) -> None:
        """
        Clean up all component pipelines.
        
        This calls cleanup on each pipeline in the sequence.
        """
        logger.debug(f"Cleaning up composed pipeline '{self.name}'")
        
        # Clean up each pipeline
        for pipeline in self.pipelines:
            try:
                await pipeline.cleanup()
            except Exception as e:
                class_name = pipeline.__class__.__name__
                error_msg = str(e)
                logger.error(f"Error cleaning up {class_name}: {error_msg}") 