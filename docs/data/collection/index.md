---
title: Data Collection
description: Documentation for data collection sources and processes
---

# Data Collection

This section documents the data collection processes and sources used in the NCAA Basketball Prediction Model.

## Data Sources

- [ESPN API Integration](espn-api-integration.md): Comprehensive documentation of ESPN API endpoints for NCAA basketball data, including game data, team information, statistics, and more.

## Collection Process

The collection pipeline fetches data from various sources, primarily the ESPN APIs, and stores it in the `data/raw` directory in Parquet format. The collection process follows these principles:

1. **Incremental Updates**: Only fetch new or changed data
2. **Structured Storage**: Data is organized by type and date
3. **Resilient Fetching**: Implements retry logic and circuit breakers
4. **Rate Limiting**: Respects API limits to avoid being blocked

## Implementation Details

The collection pipeline is implemented in `src/pipelines/collection_pipeline.py` and uses components from `src/data/collection/` to interact with different data sources.

For ESPN data specifically, the implementation follows the resilience patterns documented in [ESPN API Integration](espn-api-integration.md#error-handling-patterns) and includes comprehensive testing as outlined in the [Testing Approach](espn-api-integration.md#testing-approach-for-espn-api-integration) section. 