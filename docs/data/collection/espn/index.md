---
title: ESPN API Client
description: Documentation for the ESPN API client used to fetch NCAA basketball data
---

# ESPN API Client

The ESPN API client is a key component of our data collection pipeline, responsible for retrieving NCAA basketball data from ESPN's undocumented APIs. This section provides comprehensive documentation for the client implementation, usage patterns, and testing approaches.

## Overview

The client follows these key design principles:

- **Asynchronous**: Uses `aiohttp` for efficient concurrent requests
- **Resilient**: Implements retry logic and error handling
- **Resource-Efficient**: Manages connections and implements rate limiting
- **Type-Safe**: Comprehensive type annotations throughout
- **Well-Tested**: Extensive unit and integration tests

## Documentation Sections

- [Client Usage Guide](client-usage-guide.md): Examples and usage patterns for all endpoints
- [Technical Reference](client-reference.md): Complete API reference for all methods
- [Testing Guide](testing-guide.md): Testing strategy and approach
- [API Reference](api-reference.md): Detailed information about ESPN API endpoints

## Features

- Comprehensive implementation of all ESPN NCAA basketball endpoints
- Built-in rate limiting to prevent API throttling
- Automatic retry for transient failures
- Resource management via async context manager
- Detailed logging for all API interactions
- Consistent error handling following project patterns
- Full type annotations for developer experience

## Code Examples

Quick example for retrieving game data:

```python
import asyncio
from src.data.collection.espn.client import ESPNClient

async def fetch_games():
    async with ESPNClient() as client:
        # Get games for March 2023
        games_df = await client.get_scoreboard_for_date_range(
            start_date="20230301",
            end_date="20230331"
        )
        return games_df

# Run the async function
games = asyncio.run(fetch_games())
```

## Integration with Collection Pipeline

The ESPN client is designed to be used within the collection pipeline:

```python
from src.data.collection.espn.client import ESPNClient
from src.pipelines.collection_pipeline import CollectionPipeline

# Configure pipeline to use ESPN client for data collection
pipeline = CollectionPipeline()
pipeline.run(data_source="espn", date_range=["20230301", "20230331"])
```

## Implementation Details

The implementation is divided into three main components:

1. **Client (`client.py`)**: Core HTTP client with rate limiting and API methods
2. **Models (`models.py`)**: Pydantic models for request/response validation
3. **Parsers (`parsers.py`)**: Functions for transforming API responses to DataFrames

## Related Files

- `src/data/collection/espn/client.py`: Main client implementation
- `src/data/collection/espn/models.py`: Pydantic models for API responses
- `src/data/collection/espn/parsers.py`: Parsing functions for API responses
- `tests/data/collection/espn/test_client.py`: Tests for client functionality
- `tests/data/collection/espn/test_parsers.py`: Tests for response parsing 