---
title: Logging Strategy
description: Guidelines for logging in the NCAA Basketball Prediction Model
---

# Logging Strategy

[TOC]

This document outlines the logging approach for the NCAA Basketball Prediction Model, ensuring consistent error tracking, diagnostic information, and operational visibility.

## Logging Framework

The project uses Python's built-in `logging` module with structured logging enhancements via the `structlog` package:

```python
# Requirements in pyproject.toml
# structlog>=23.1.0
# rich>=13.3.5  # For console formatting
```

### Core Benefits

1. **Structured Logging**: JSON-formatted logs for easier parsing and analysis
2. **Contextual Information**: Automatic inclusion of context (module, function, timestamp)
3. **Flexible Outputs**: Console, file, and potential external integrations
4. **Performance**: Minimal overhead in production environments

## Logger Configuration

Logger configuration is centralized in `src/utils/logging.py` and integrated with the configuration management system:

```python
import logging
import sys
from typing import Optional, Dict, Any

import structlog
from rich.console import Console
from rich.logging import RichHandler
from utils.config import get_config

console = Console(width=150)

def configure_logging() -> None:
    """Configure application-wide logging using settings from config system."""
    config = get_config()
    log_level = config.logging.level
    json_logs = config.logging.json_format
    log_file = config.logging.file

    level = getattr(logging, log_level.upper())

    # Processors for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        # JSON formatter for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Rich console formatter for development
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handlers = []

    # Console handler with Rich formatting
    console_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        markup=True,
        show_time=False,  # structlog adds timestamps
    )
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        handlers.append(file_handler)

    # Root logger configuration
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
    )
```

## Usage Patterns

### Basic Usage

```python
import structlog

logger = structlog.get_logger(__name__)

def process_team_data(team_id: str) -> None:
    logger.info("Processing team data", team_id=team_id)
    try:
        # Processing logic
        pass
    except Exception as e:
        logger.exception("Failed to process team data", team_id=team_id)
        raise
```

### Context Managers

For operations spanning multiple functions, use context variables:

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger(__name__)

def process_pipeline(date: str) -> None:
    # Bind context that will be included in all log entries
    bind_contextvars(
        pipeline="ingest",
        date=date
    )

    logger.info("Starting pipeline")
    try:
        # Pipeline operations
        fetch_data(date)
        process_data()
        logger.info("Pipeline completed successfully")
    except Exception:
        logger.exception("Pipeline failed")
        raise
    finally:
        # Clear context when done
        clear_contextvars()
```

## Log Levels

Use appropriate log levels for different types of information:

| Level | Purpose | Example |
|-------|---------|---------|
| DEBUG | Detailed diagnostic information | `logger.debug("Parsing response", data_size=len(data))` |
| INFO | Confirmation of normal operations | `logger.info("Processed 20 teams")` |
| WARNING | Unexpected but non-critical issues | `logger.warning("Rate limit approaching", remaining=10)` |
| ERROR | Errors preventing specific operations | `logger.error("Failed to fetch team data", team_id=123)` |
| CRITICAL | Critical errors affecting the system | `logger.critical("Database connection failed")` |

## Log Organization

Logs are organized in the following ways:

1. **By Module**: Each module has its own logger with the module name
2. **By Process**: Pipeline processes include context about which pipeline is running
3. **By Environment**: Different log formats for development (rich console) and production (JSON)

### Log Storage

For production deployments:

- Console logs are captured by the process runner
- File logs are rotated daily with a 30-day retention:
  ```python
  from logging.handlers import TimedRotatingFileHandler

  handler = TimedRotatingFileHandler(
      "logs/app.log",
      when="midnight",
      backupCount=30
  )
  ```

## Log Analysis

For local development, logs are displayed in a readable format in the console.

For production, JSON-formatted logs can be:
- Ingested into log aggregation systems (e.g., ELK stack, Datadog)
- Parsed for metrics and alerting
- Analyzed for debugging and performance tracking

## Implementation

1. Include `structlog` and `rich` in the project dependencies
2. Add the logging configuration to application startup
3. Create a module-specific logger at the top of each file
4. Use structured logging with explicit parameter names
