---
title: ESPN Client Testing Guide
description: Guide for testing the ESPN client, including test strategies, fixtures, and mocking approaches
---

# ESPN Client Testing Guide

This guide outlines the testing approach for the ESPN client, including test strategies, fixtures, and mocking approaches.

## Test Strategy

The ESPN client testing follows a comprehensive strategy that includes:

1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Testing the client's interaction with mock API responses
3. **Error Handling Tests**: Verifying the client handles errors appropriately
4. **Rate Limiting Tests**: Ensuring rate limiting functions correctly

## Test Structure

Tests for the ESPN client are located in:

```
tests/data/collection/espn/
├── conftest.py           # Shared fixtures and configuration
├── fixtures/             # Mock API response fixtures
│   ├── scoreboard_response.json
│   ├── team_response.json
│   ├── teams_response.json
│   └── game_summary_response.json
├── test_client.py        # Tests for client functionality
└── test_parsers.py       # Tests for response parsing
```

## Test Fixtures

Test fixtures provide mock API responses that simulate real ESPN API data without requiring actual API calls. These fixtures are stored as JSON files in the `fixtures/` directory.

### Example Fixture Usage

```python
import json
import os
import pytest

@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file from the fixtures directory."""
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load

def test_scoreboard_parsing(load_fixture):
    """Test parsing of scoreboard data."""
    # Load the fixture
    mock_data = load_fixture("scoreboard_response.json")
    
    # Use the fixture data for testing
    # ...
```

## Mocking Approach

The ESPN client tests use mocking to isolate the client from external dependencies:

1. **HTTP Client Mocking**: Using `unittest.mock.patch` to replace the `httpx.AsyncClient`
2. **API Response Mocking**: Using fixtures to provide realistic API responses
3. **Rate Limiter Mocking**: Testing rate limiting behavior with controlled timing

### Example Mocking Pattern

```python
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
class TestESPNClient:
    async def test_get_scoreboard_success(self, load_fixture):
        """Test successful scoreboard data retrieval."""
        # Mock the API response
        mock_response = load_fixture("scoreboard_response.json")
        
        async with ESPNClient() as client:
            # Mock the _get method to return our fixture
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                
                # Call the method being tested
                result = await client.get_scoreboard("20230301")
                
                # Assertions
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                mock_get.assert_called_once()
```

## Test Categories

### Client Initialization Tests

These tests verify the client initializes correctly:

```python
async def test_client_initialization(self):
    """Test that client is properly initialized."""
    async with ESPNClient() as client:
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)
```

### API Method Tests

These tests verify each API method functions correctly:

```python
async def test_get_teams(self, load_fixture):
    """Test teams retrieval."""
    mock_response = load_fixture("teams_response.json")
    
    async with ESPNClient() as client:
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_teams()
            
            assert isinstance(result, pl.DataFrame)
            assert not result.is_empty()
            mock_get.assert_called_once()
```

### Error Handling Tests

These tests verify the client handles errors appropriately:

```python
async def test_get_scoreboard_invalid_date(self):
    """Test that invalid date raises ValueError."""
    async with ESPNClient() as client:
        with pytest.raises(ValueError):
            await client.get_scoreboard("invalid-date")
```

### Retry Logic Tests

These tests verify the retry logic functions correctly:

```python
async def test_retry_on_failure(self):
    """Test that retry mechanism works on transient failures."""
    async with ESPNClient() as client:
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                httpx.HTTPError("Connection error"),
                httpx.HTTPError("Timeout"),
                {"data": "success"}
            ]
            
            result = await client._test_method_with_retry()
            assert result == {"data": "success"}
            assert mock_get.call_count == 3
```

### Rate Limiting Tests

These tests verify the rate limiting functions correctly:

```python
async def test_rate_limiting(self):
    """Test that rate limiter properly limits request rate."""
    limiter = RateLimiter(rate=10.0, burst=2)
    
    # Should be able to make 2 requests immediately
    await limiter.acquire()
    await limiter.acquire()
    
    # Third request should be delayed
    start_time = asyncio.get_event_loop().time()
    await limiter.acquire()
    duration = asyncio.get_event_loop().time() - start_time
    
    # With rate=10.0, each request after burst should take ~0.1s
    assert duration >= 0.05
```

## Running Tests

To run the ESPN client tests:

```bash
# Run all ESPN client tests
pytest tests/data/collection/espn/

# Run with increased verbosity
pytest -v tests/data/collection/espn/

# Run a specific test file
pytest tests/data/collection/espn/test_client.py

# Run a specific test
pytest tests/data/collection/espn/test_client.py::TestESPNClient::test_client_initialization
```

## Test Coverage

To ensure comprehensive test coverage, the ESPN client tests should cover:

1. **All Public Methods**: Each method exposed by the client
2. **Error Paths**: All error conditions and exception handling
3. **Edge Cases**: Boundary conditions and unusual inputs
4. **Resource Management**: Proper initialization and cleanup

## Adding New Tests

When adding new functionality to the ESPN client, follow these steps to add tests:

1. **Add Fixtures**: Create new JSON fixtures for any new API endpoints
2. **Add Unit Tests**: Test the new functionality in isolation
3. **Add Integration Tests**: Test the new functionality with mock API responses
4. **Add Error Handling Tests**: Test error conditions for the new functionality

## Test Design Principles

Follow these principles when designing tests for the ESPN client:

1. **Isolation**: Tests should not depend on external services
2. **Repeatability**: Tests should be deterministic and repeatable
3. **Clarity**: Test names and assertions should clearly indicate intent
4. **Comprehensiveness**: Tests should cover both success and failure cases

## Troubleshooting Tests

If ESPN client tests are failing, consider these common issues:

1. **Fixture Format**: Ensure fixture data matches expected API responses
2. **Mocking Setup**: Verify that mocks are correctly configured
3. **Async Context**: Ensure tests are properly set up for async testing
4. **Rate Limiting**: Check for timing-dependent test failures 