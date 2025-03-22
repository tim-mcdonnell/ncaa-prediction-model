"""Integration tests for scoreboard data ingestion.

These tests verify the end-to-end behavior of the scoreboard ingestion process,
including performance, error handling, and adaptive backoff behavior.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from structlog import get_logger

from src.ingest.scoreboard import (
    ScoreboardIngestion,
)
from src.utils.config import ESPNApiConfig, RequestSettings
from src.utils.espn_api_client import ESPNApiClient

logger = get_logger()

# Test constants
TEST_DB_PATH = "tests/data/test_integration.duckdb"
TEST_DATES = ["2023-03-01", "2023-03-02", "2023-03-03", "2023-03-04", "2023-03-05"]


class TestScoreboardIngestionIntegration:
    """Integration tests for scoreboard data ingestion."""

    @pytest.fixture()
    def espn_api_config(self):
        """Create a test ESPN API configuration."""
        # Create RequestSettings with test values
        request_settings = RequestSettings(
            initial_request_delay=0.05,  # Fast for testing
            max_retries=2,
            timeout=1.0,
            batch_size=10,
            max_concurrency=3,
            min_request_delay=0.01,
            max_request_delay=0.5,
            backoff_factor=1.5,
            recovery_factor=0.9,
            error_threshold=2,
            success_threshold=3,
        )

        # Create ESPNApiConfig with the request_settings
        config = ESPNApiConfig(
            base_url=(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
            ),
            endpoints={"scoreboard": "scoreboard"},
            request_settings=request_settings,
        )

        # Add historical_start_date as an attribute for testing
        config.historical_start_date = "2022-11-01"

        return config

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

        # Track written data
        stored_data = {}

        # Create a patched version of fetch_and_store_date_async
        async def mock_fetch_and_store(self, date, db=None):
            # Call the original fetch
            espn_date = date.replace("-", "")
            data = create_mock_response(espn_date)
            # Store the data in our tracked dictionary
            stored_data[date] = data
            # Return the data as the original method would
            return data

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                mock_fetch_and_store,
            ),
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

        # Each date should have data stored
        assert len(stored_data) == len(TEST_DATES)
        for date in TEST_DATES:
            assert date in stored_data

            # Verify data structure
            data = stored_data[date]
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

        mock_sync_client.fetch_scoreboard.side_effect = mock_fetch_sync

        # Create async mock
        mock_async_client = MagicMock(spec=ESPNApiClient)
        mock_async_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        async def mock_fetch_async(date):
            # Simulate API delay - concurrent
            await asyncio.sleep(fixed_delay)
            espn_date = date.replace("-", "")
            return create_mock_response(espn_date)

        mock_async_client.fetch_scoreboard_async.side_effect = mock_fetch_async

        # Mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.write_scoreboard_data.return_value = {"success": True}
        mock_parquet.get_processed_dates.return_value = []

        # Custom sequential function to avoid calling process_date_range which would try to
        # use asyncio.run()
        sequential_results = []

        def custom_sequential_fetch(date):
            result = mock_fetch_sync(date)
            mock_parquet.write_scoreboard_data(
                date=date,
                source_url="https://example.com/endpoint",
                parameters={"dates": date.replace("-", ""), "groups": "50", "limit": 200},
                data=result,
            )
            sequential_results.append(date)
            return result

        # Patch necessary components
        with (
            patch("src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet),
        ):
            # Measure sequential performance using a custom implementation
            sequential_start = time.time()
            for date in test_dates:
                custom_sequential_fetch(date)
            sequential_duration = time.time() - sequential_start

            # Run concurrent version
            concurrent_ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            concurrent_ingestion.api_client = mock_async_client

            # Measure concurrent performance
            concurrent_start = time.time()
            concurrent_result = await concurrent_ingestion.process_date_range_async(test_dates)
            concurrent_duration = time.time() - concurrent_start

        # Assert
        # Both should process the same number of dates
        assert len(sequential_results) == len(test_dates)
        assert len(concurrent_result) == len(test_dates)

        # Concurrent should be faster (at least 1.5x since we're using multiple workers)
        # Calculate speedup factor
        speedup = sequential_duration / concurrent_duration
        min_expected_speedup = 1.5  # Should be at least 50% faster

        logger.info(
            "Performance comparison",
            sequential_duration=sequential_duration,
            concurrent_duration=concurrent_duration,
            speedup=speedup,
            test_dates=len(test_dates),
        )

        assert (
            speedup > min_expected_speedup
        ), f"Concurrent should be at least {min_expected_speedup}x faster than sequential"

    @pytest.mark.asyncio()
    async def test_async_error_handling_with_simulated_api_failures(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test async error handling with simulated API failures."""
        # Arrange
        # Some dates will fail, others will succeed
        failures = {TEST_DATES[1], TEST_DATES[3]}  # 2nd and 4th dates will fail
        successful_dates = [date for date in TEST_DATES if date not in failures]

        processed_dates = []

        # Mock fetch_and_store_date_async with selective failures
        async def mock_fetch_and_store(date, *args, **kwargs):
            if date in failures:
                error_msg = f"Simulated API failure for date {date}"
                raise Exception(error_msg)

            processed_dates.append(date)
            return {"events": [{"id": f"event_{date}"}]}

        # Mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.write_scoreboard_data.return_value = {"success": True}
        mock_parquet.get_processed_dates.return_value = []

        # Patch necessary components
        with (
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
            patch("src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet),
        ):
            # Act - using directly instantiated class for testing
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            result = await ingestion.process_date_range_async(TEST_DATES)

        # Assert
        # Only successful dates should be in the result
        assert len(result) == len(successful_dates)
        assert sorted(result) == sorted(successful_dates)
        assert sorted(processed_dates) == sorted(successful_dates)

        # Verify expected failures
        for date in TEST_DATES:
            if date in failures:
                assert date not in result
            else:
                assert date in result

    @pytest.mark.asyncio()
    async def test_backoff_strategy_behavior_with_simulated_rate_limits(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test that the system can handle rate limits by retrying."""
        # Configure mock responses
        request_counts = {}

        # Mock the low-level _request_async method to simulate rate limits then success
        async def mock_request_async(url, params=None):
            date = params.get("dates") if params else None
            if not date:
                return {}

            # Initialize request counter for this date
            if date not in request_counts:
                request_counts[date] = 0

            # Increment request counter
            request_counts[date] += 1

            # First request fails with rate limit, second succeeds
            if request_counts[date] == 1:
                raise httpx.HTTPStatusError(
                    "429 Too Many Requests",
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )

            # Create a response with events for this date
            return {"events": [{"id": f"event_{date}"}]}

        # Mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.write_scoreboard_data.return_value = {"success": True}
        mock_parquet.get_processed_dates.return_value = []

        # Create a real API client with a fast retry configuration
        request_settings = RequestSettings(
            initial_request_delay=0.01,
            max_retries=3,
            timeout=0.1,
            max_concurrency=2,
            min_request_delay=0.01,
            max_request_delay=0.1,
            backoff_factor=1.1,
            recovery_factor=0.9,
        )

        test_config = ESPNApiConfig(
            base_url="https://example.com",
            endpoints={"scoreboard": "scoreboard"},
            request_settings=request_settings,
        )

        # Use a subset of dates for this test
        test_dates = TEST_DATES[:2]  # Just two dates
        formatted_dates = [date.replace("-", "") for date in test_dates]

        # Patch the necessary components
        with (
            patch(
                "src.utils.espn_api_client.ESPNApiClient._request_async",
                side_effect=mock_request_async,
            ),
            patch("src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet),
            patch("asyncio.sleep", AsyncMock()),  # Don't actually sleep during tests
        ):
            # Create ingestion with our test config
            ingestion = ScoreboardIngestion(
                test_config,
                TEST_DB_PATH,
                skip_existing=False,
            )

            # Process the dates
            result = await ingestion.process_date_range_async(test_dates)

            # Verify all dates were processed despite rate limits
            assert len(result) == len(test_dates)
            assert sorted(result) == sorted(test_dates)

            # Verify each date was requested exactly twice (one failure, one success)
            for date in formatted_dates:
                assert request_counts[date] == 2
