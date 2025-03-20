"""Integration tests for scoreboard data ingestion.

These tests verify the end-to-end behavior of the scoreboard ingestion process,
including performance, error handling, and adaptive backoff behavior.
"""

import asyncio
import time
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ingest.scoreboard import (
    ScoreboardIngestion,
)
from src.utils.config import ESPNApiConfig
from src.utils.database import Database
from src.utils.espn_api_client import ESPNApiClient

# Test constants
TEST_DB_PATH = "tests/data/test_integration.duckdb"
TEST_DATES = ["2023-03-01", "2023-03-02", "2023-03-03", "2023-03-04", "2023-03-05"]


class TestScoreboardIngestionIntegration:
    """Integration tests for scoreboard data ingestion."""

    @pytest.fixture()
    def espn_api_config(self):
        """Create a test ESPN API configuration."""
        return ESPNApiConfig(
            base_url=(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
            ),
            endpoints={"scoreboard": "scoreboard"},
            initial_request_delay=0.05,  # Fast for testing
            max_retries=2,
            timeout=1.0,
            historical_start_date="2022-11-01",
            batch_size=10,
            max_concurrency=3,
            min_request_delay=0.01,
            max_request_delay=0.5,
            backoff_factor=1.5,
            recovery_factor=0.9,
            error_threshold=2,
            success_threshold=3,
        )

    @pytest.fixture()
    def mock_db(self):
        """Create a mock database that tracks inserts."""
        mock = MagicMock()
        mock.get_processed_dates.return_value = []  # No dates processed initially
        mock.inserted_data = {}

        def mock_insert(date, **kwargs):
            mock.inserted_data[date] = kwargs.get("data")

        mock.insert_bronze_scoreboard.side_effect = mock_insert
        return mock

    @pytest.fixture()
    def mock_response_factory(self):
        """Factory for creating mock API responses."""

        def create_mock_response(date):
            """Create a mock response for a given date."""
            return {
                "events": [
                    {
                        "id": f"event_{date}_{i}",
                        "date": f"2023-03-15T{20 + i}:00Z",
                        "name": f"Game {i} on {date}",
                        "competitions": [
                            {
                                "id": f"comp_{date}_{i}",
                                "status": {"type": {"completed": True}},
                                "competitors": [
                                    {"team": {"id": "52", "score": "75"}},
                                    {"team": {"id": "2", "score": "70"}},
                                ],
                            }
                        ],
                    }
                    for i in range(2)  # 2 events per date
                ]
            }

        return create_mock_response

    @pytest.mark.asyncio()
    async def test_end_to_end_async_flow_with_mocked_api(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test the end-to-end asynchronous flow with a mocked API."""
        # Arrange
        create_mock_response = mock_response_factory

        # Create async mock for API client
        mock_api_client = MagicMock(spec=ESPNApiClient)
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Setup async fetch method
        async def mock_fetch_async(date):
            # Simulate API delay
            await asyncio.sleep(0.01)
            espn_date = date.replace("-", "")
            return create_mock_response(espn_date)

        mock_api_client.fetch_scoreboard_async = AsyncMock(side_effect=mock_fetch_async)

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Act
            # Create direct instance for testing
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)

            # Execute async processing
            result = await ingestion.process_date_range_async(TEST_DATES)

        # Assert
        # All dates should be processed
        assert len(result) == len(TEST_DATES)
        assert sorted(result) == sorted(TEST_DATES)

        # Each date should have a corresponding API call
        expected_call_count = len(TEST_DATES)
        assert mock_api_client.fetch_scoreboard_async.call_count == expected_call_count

        # Each date should be stored in the database
        assert len(mock_db.inserted_data) == len(TEST_DATES)
        for date in TEST_DATES:
            assert date in mock_db.inserted_data

            # Verify data structure
            data = mock_db.inserted_data[date]
            assert "events" in data
            events_per_date = 2  # Number of events per date in mock data
            assert len(data["events"]) == events_per_date

    @pytest.mark.asyncio()
    async def test_performance_improvement_with_concurrent_vs_sequential(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test performance improvement of concurrent vs sequential processing."""
        # Arrange
        create_mock_response = mock_response_factory
        test_dates = TEST_DATES * 2  # More dates for better performance comparison
        fixed_delay = 0.05  # Fixed delay per request for consistent testing

        # Create sync mock
        mock_sync_client = MagicMock(spec=ESPNApiClient)
        mock_sync_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        def mock_fetch_sync(date):
            # Simulate API delay - sequential
            time.sleep(fixed_delay)
            espn_date = date.replace("-", "")
            return create_mock_response(espn_date)

        mock_sync_client.fetch_scoreboard = MagicMock(side_effect=mock_fetch_sync)

        # Create async mock
        mock_async_client = MagicMock(spec=ESPNApiClient)
        mock_async_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        async def mock_fetch_async(date):
            # Simulate same API delay - but concurrent
            await asyncio.sleep(fixed_delay)
            espn_date = date.replace("-", "")
            return create_mock_response(espn_date)

        mock_async_client.fetch_scoreboard_async = AsyncMock(side_effect=mock_fetch_async)

        # Measures sync performance
        def measure_sync_performance():
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            ingestion.api_client = mock_sync_client

            # Override process_date_range to avoid calling async version
            def sync_process(dates):
                with Database(ingestion.db_path) as db:
                    processed_dates = []
                    for date in dates:
                        ingestion.fetch_and_store_date(date, db)
                        processed_dates.append(date)
                return processed_dates

            # Use monkeypatch instead of direct assignment
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setattr(ingestion, "process_date_range", sync_process)

            start_time = time.time()
            ingestion.process_date_range(test_dates)
            end_time = time.time()
            monkeypatch.undo()
            return end_time - start_time

        # Measure async performance
        async def measure_async_performance():
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            ingestion.api_client = mock_async_client

            start_time = time.time()
            await ingestion.process_date_range_async(test_dates)
            end_time = time.time()
            return end_time - start_time

        # Patch components for both tests
        with (
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # First measure sync
            sync_time = measure_sync_performance()

            # Then measure async
            async_time = await measure_async_performance()

        # Assert
        # Async should be significantly faster with concurrent requests
        # Theoretical improvement: (num_dates * delay) vs (num_batches * delay)
        # With max_concurrency=3, we expect at least 2-3x improvement
        expected_min_speedup = 1.5  # Conservative estimate
        actual_speedup = sync_time / async_time

        assert actual_speedup >= expected_min_speedup, (
            f"Expected speedup of at least {expected_min_speedup}x, but got {actual_speedup}x. "
            f"Sync: {sync_time:.2f}s, Async: {async_time:.2f}s"
        )

    @pytest.mark.asyncio()
    async def test_async_error_handling_with_simulated_api_failures(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test async error handling with simulated API failures."""
        # Arrange
        create_mock_response = mock_response_factory

        # Create async mock with deliberate errors
        mock_api_client = MagicMock(spec=ESPNApiClient)
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Add an error counter to track error handling
        error_count = 0
        expected_errors = 2  # Number of errors we expect to encounter
        api_calls = set()  # Track which dates had API calls

        # Setup async fetch method with errors
        async def mock_fetch_async(date):
            nonlocal error_count
            api_calls.add(date)  # Track which date is being processed

            # Simulate different error scenarios based on date
            if date == "20230302":  # Already in API format (YYYYMMDD)
                # Simulate rate limit error
                error_count += 1
                error_msg = "429 Too Many Requests"
                raise httpx.HTTPStatusError(
                    error_msg,
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )
            elif date == "20230304":  # Already in API format (YYYYMMDD)
                # Simulate server error
                error_count += 1
                error_msg = "500 Internal Server Error"
                raise httpx.HTTPStatusError(
                    error_msg,
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            else:
                # Normal response
                await asyncio.sleep(0.01)
                return create_mock_response(date)

        mock_api_client.fetch_scoreboard_async = AsyncMock(side_effect=mock_fetch_async)

        # Track what dates had data inserted
        successful_inserts = set()

        # Mock the insert_bronze_scoreboard method to track successful inserts
        def insert_tracking(date, **_):
            successful_inserts.add(date)

        mock_db.insert_bronze_scoreboard = insert_tracking

        # Create test dates in YYYY-MM-DD format that will be converted to YYYYMMDD
        formatted_test_dates = [d.replace("-", "") for d in TEST_DATES]

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
            # Mock format_date_for_api to just return the date as is
            # (since we're using pre-formatted dates)
            patch(
                "src.ingest.scoreboard.format_date_for_api",
                side_effect=lambda x: x.replace("-", ""),
            ),
        ):
            # Act
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            ingestion.api_client = mock_api_client

            # Execute async processing
            await ingestion.process_date_range_async(TEST_DATES)

        # Assert
        # All dates should have API call attempts (in ESPN format - YYYYMMDD)
        assert mock_api_client.fetch_scoreboard_async.call_count == len(TEST_DATES)
        assert api_calls == set(formatted_test_dates)

        # We should have encountered exactly 2 errors
        assert (
            error_count == expected_errors
        ), f"Expected {expected_errors} errors, but got {error_count}"

        # Only successful dates should be inserted into the database (in YYYY-MM-DD format)
        expected_success = {"2023-03-01", "2023-03-03", "2023-03-05"}
        assert successful_inserts == expected_success

    @pytest.mark.asyncio()
    async def test_backoff_strategy_behavior_with_simulated_rate_limits(self, espn_api_config):
        """Test backoff strategy behavior with simulated rate limits."""
        # Arrange
        # Create a client that tracks delay changes
        delay_history = []
        concurrency_history = []

        # Create base API client
        api_client = ESPNApiClient(espn_api_config)

        # Constants for test thresholds
        error_simulation_count = 3
        success_check_index = 4

        async def tracking_request(_, _params=None):
            # Record current state
            delay_history.append(api_client.current_request_delay)
            concurrency_history.append(api_client.max_concurrency)

            # Simulate rate limit error for first few calls
            if len(delay_history) <= error_simulation_count:
                # Trigger backoff by simulating rate limit
                api_client._track_request_result(success=False, status_code=429)
                error_msg = "429 Too Many Requests"
                raise httpx.HTTPStatusError(
                    error_msg,
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )

            # Then succeed and trigger recovery
            api_client._track_request_result(success=True)
            return {"events": [{"id": "test"}]}

        # Replace request method with our tracking version using monkeypatch
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(api_client, "_request_async", tracking_request)
        monkeypatch.setattr(
            api_client, "_retry_request_async", tracking_request
        )  # Skip retries for this test

        # Act - just make a series of requests and observe backoff behavior
        try:
            for _ in range(6):
                with suppress(httpx.HTTPStatusError):
                    await api_client._request_async("https://example.com")
        finally:
            # Undo the monkeypatching
            monkeypatch.undo()

        # Assert
        # Delay should increase after each error
        assert delay_history[1] > delay_history[0], "Delay should increase after error"
        assert (
            delay_history[2] > delay_history[1]
        ), "Delay should continue to increase after multiple errors"

        # After reaching error threshold, concurrency should decrease
        assert (
            min(concurrency_history) < espn_api_config.max_concurrency
        ), "Concurrency should decrease after persistent errors"

        # Delay should decrease or stay the same after successful calls
        # Depending on recovery_factor and success_threshold,
        # it might take more than one success to decrease
        if len(delay_history) > success_check_index:
            assert (
                delay_history[success_check_index] <= delay_history[success_check_index - 1]
            ), "Delay should decrease or remain stable after success"
