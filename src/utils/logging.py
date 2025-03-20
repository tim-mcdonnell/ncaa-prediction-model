"""Logging configuration for the NCAA Basketball Prediction Model.

This module provides structured logging setup using structlog, with support for
both console and file logging, and configurable log levels and formats.
"""

import logging
import sys
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(
    log_level: str = "INFO",
    json_logs: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        log_file: Optional path to log file
    """
    # Set up stdlib logging
    level = getattr(logging, log_level.upper())

    # Set up handlers
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        # Create parent directories if they don't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    # Configure basic logging
    logging.basicConfig(format="%(message)s", level=level, handlers=handlers)

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
    ]

    if json_logs:
        # JSON formatter for production
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console formatter for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
