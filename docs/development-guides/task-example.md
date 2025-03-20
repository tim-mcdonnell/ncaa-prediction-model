---
title: Task Example
description: An example of a well-structured implementation task for the NCAA Basketball Analytics Project
---

# Task Example: Implement ESPN Scoreboard Data Ingestion Pipeline

> **Note**: This document is an improved template for creating implementation tasks, based on lessons learned from GitHub Issue #1.

## Summary

Create a data ingestion module to fetch NCAA basketball scoreboard data from the ESPN API and store it in the bronze layer following our medallion architecture. This component will establish patterns for future ingestion modules.

## 🔍 Background

The NCAA basketball prediction model requires historical game data as its foundation. ESPN's API provides this data through their scoreboard endpoint, which we need to ingest into our database for further processing.

## 🎯 Objectives

- Build a data ingestion pipeline for NCAA basketball scoreboard data
- Store raw data in the bronze layer of our DuckDB database
- Follow project architecture and coding standards
- Establish patterns for future ingestion modules

## 📋 Development Process (TDD)

This task **MUST** follow Test-Driven Development as outlined in [CONTRIBUTING.md](../../CONTRIBUTING.md):

1. **RED** 📕 First, write failing tests that define expected behavior
2. **GREEN** 📗 Then, implement minimal code to make tests pass
3. **REFACTOR** 📘 Finally, improve code while maintaining passing tests

### Required Test Cases

Write tests for:

1. **Unit Tests**:
   - `test_fetch_scoreboard_data_with_valid_date_returns_expected_structure`
   - `test_fetch_scoreboard_data_with_invalid_date_raises_appropriate_error`
   - `test_insert_bronze_scoreboard_with_new_data_succeeds`
   - `test_insert_bronze_scoreboard_with_duplicate_data_is_idempotent`
   - `test_process_date_range_processes_all_dates_in_range`
   - `test_process_date_range_skips_already_processed_dates`
   - `test_cli_command_with_various_date_parameters`

2. **Integration Tests**:
   - `test_end_to_end_flow_with_mocked_api`
   - `test_error_handling_with_simulated_api_failures`

3. **Real-World Data Test**:
   - Include at least one test with sanitized real-world data to verify actual API response structure handling

## 🏗️ Architecture Alignment

This implementation must strictly adhere to our established architecture:

1. **Database Structure** 📊
   - Use a **single DuckDB database** file at `data/ncaa.duckdb`
   - Create a bronze layer table named `bronze_scoreboard`
   - Include all required metadata fields
   - **DO NOT** create separate database files for different layers

2. **Table Schema** 📝
   ```sql
   CREATE TABLE IF NOT EXISTS bronze_scoreboard (
       id INTEGER PRIMARY KEY,
       date VARCHAR,
       source_url VARCHAR,
       parameters VARCHAR,
       content_hash VARCHAR,
       raw_data VARCHAR,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )
   ```

3. **CLI Integration** 🖥️
   - Follow standard command format: `python run.py ingest scoreboard [options]`
   - Support all required date parameters
   - Use configuration for default values

## 📦 Technical Requirements

### API Integration
- Endpoint: `/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`
- Parameters:
  - `dates=YYYYMMDD` (date-specific data)
  - `groups=50` (Division I games)
  - `limit=200` (handle days with many games)
- Request throttling and timeout handling

### Data Storage
- Store complete raw JSON in `raw_data` column
- Generate content hash for idempotent operations
- Include metadata: date, source, parameters

### Error Handling
- Implement retries with exponential backoff
- Handle and log API failures appropriately
- Validate and sanitize input parameters

## ✅ Implementation Verification Steps

1. **Test With Real Data**
   - Run with a specific date: `python run.py ingest scoreboard --date 2023-03-15`
   - Run with a date range: `python run.py ingest scoreboard --start-date 2023-03-01 --end-date 2023-03-10`
   - Verify data is correctly stored in the database

2. **Check Database Integration**
   - Verify data exists in the correct table in `data/ncaa.duckdb`
   - Verify the table structure follows the required schema
   - Validate data can be queried successfully

3. **Verify Error Handling**
   - Test behavior with network interruptions
   - Verify retry logic works as expected
   - Ensure invalid inputs are handled appropriately

## 📚 Required Documentation

1. **Code Documentation**
   - Add docstrings to all public functions and classes
   - Include type hints for all parameters and return values
   - Document parameters, return values, and exceptions

2. **Usage Documentation**
   - Create or update `docs/usage/data_ingestion.md` with:
     - Basic usage examples
     - Configuration options
     - Common troubleshooting steps

3. **Architecture Documentation**
   - Update `docs/architecture/data-pipeline.md` with specific implementation details
   - Add diagrams if helpful to understand the flow

## 🔄 Implementation Workflow

Follow these steps to complete the task:

1. **Review Architecture**: Read all linked documentation before starting
2. **Write Tests First**: Implement all test cases before writing implementation code
3. **Implement Functionality**: Make tests pass with minimal implementation
4. **Refactor**: Clean up code while maintaining passing tests
5. **Test With Real Data**: Validate using actual API responses
6. **Document**: Add all required documentation
7. **Final Review**: Verify all architecture requirements are met

## 📏 Acceptance Criteria

1. ✅ All automated tests pass (unit and integration)
2. ✅ Code successfully ingests data with real API responses
3. ✅ Idempotent operations work as expected (no duplicates)
4. ✅ All data is stored in the correct DuckDB table
5. ✅ Error handling works with appropriate retries
6. ✅ CLI commands function as documented
7. ✅ Documentation is complete and accurate
8. ✅ All code quality checks pass (linting, typing, etc.)
9. ✅ Architecture alignment is verified
10. ✅ Review includes running with real data for at least 7 days

## 📖 Related Documentation

- [Architecture Overview](../architecture/index.md)
- [Data Pipeline](../architecture/data-pipeline.md)
- [Data Directory Structure](../architecture/data-directory-structure.md)
- [Configuration Management](../architecture/configuration-management.md)
- [Logging Strategy](../architecture/logging-strategy.md)
- [ESPN API Reference](../espn-api-reference.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
