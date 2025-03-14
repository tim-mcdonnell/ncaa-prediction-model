"""
Logging Configuration

This module provides a standardized logging configuration for the NCAA prediction model.
It sets up structured logging with appropriate formatting and handlers.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

# Default log format - structured format with timestamps and log levels
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Default log directory - relative to project root
DEFAULT_LOG_DIR = "logs"


def setup_logging(
    log_level: int = logging.INFO,
    log_format: str = DEFAULT_LOG_FORMAT,
    log_file: Optional[Union[str, Path]] = None,
    log_dir: Optional[Union[str, Path]] = None,
    module_name: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logging for the application or a specific module.
    
    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_format: Format string for log messages
        log_file: Optional specific log file path
        log_dir: Optional directory for log files (default is "logs")
        module_name: Optional module name for the logger
    
    Returns:
        Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger(module_name if module_name else "ncaa_prediction")
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(log_format)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Set up file logging if requested
        if log_file or log_dir:
            if not log_file:
                # Create log directory if needed
                log_dir = log_dir or DEFAULT_LOG_DIR
                os.makedirs(log_dir, exist_ok=True)
                
                # Create default log filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_name = f"{module_name or 'ncaa'}.{timestamp}.log"
                log_file = os.path.join(log_dir, log_name)
            
            # Create file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10485760, backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    return logger


def get_pipeline_logger(pipeline_name: str) -> logging.Logger:
    """
    Get a logger configured specifically for a pipeline component.
    
    Args:
        pipeline_name: Name of the pipeline component
    
    Returns:
        Configured logger for the pipeline
    """
    # Create log directory structure
    log_dir = os.path.join(DEFAULT_LOG_DIR, "pipelines")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file for this pipeline
    module_name = f"pipeline.{pipeline_name}"
    
    return setup_logging(
        log_level=logging.INFO,
        module_name=module_name,
        log_dir=log_dir
    )
