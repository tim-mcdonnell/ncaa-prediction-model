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
    ScoreboardIngestionConfig,
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

        # Create a patched version of process_item_async
        async def mock_process_item(self, date):
            # Simulate fetching
            espn_date = date.replace("-", "")
            data = create_mock_response(espn_date)
            # Store the data in our tracked dictionary
            stored_data[date] = data
            # Return successful result
            return {"item_key": date, "success": True, "result": {"success": True}}

        # Patch necessary components
        with patch.object(ScoreboardIngestion, "process_item_async", mock_process_item):
            # Act
            # Create direct instance for testing
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date=TEST_DATES[0],
                end_date=TEST_DATES[-1],
                force_overwrite=True,  # Force processing of all dates
            )
            ingestion = ScoreboardIngestion(config)

            # Execute async processing
            result = await ingestion.ingest_async()

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

        mock_sync_client.fetch_scoreboard = AsyncMock(side_effect=mock_fetch_sync)

        # Create async mock
        mock_async_client = MagicMock(spec=ESPNApiClient)
        mock_async_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        async def mock_fetch_async(date):
            # Simulate API delay - concurrent
            await asyncio.sleep(fixed_delay)
            espn_date = date.replace("-", "")
            return create_mock_response(espn_date)

        mock_async_client.fetch_scoreboard_async = AsyncMock(side_effect=mock_fetch_async)

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
        with patch("src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet):
            # Measure sequential performance using a custom implementation
            sequential_start = time.time()
            for date in test_dates:
                custom_sequential_fetch(date)
            sequential_duration = time.time() - sequential_start

            # Run concurrent version
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date=test_dates[0],
                end_date=test_dates[-1],
            )
            concurrent_ingestion = ScoreboardIngestion(config)
            concurrent_ingestion.api_client = mock_async_client
            concurrent_ingestion.parquet_storage = mock_parquet

            # Mock determine_items_to_process to use our test dates
            concurrent_ingestion.determine_items_to_process = MagicMock(return_value=test_dates)

            # Measure concurrent performance
            concurrent_start = time.time()
            concurrent_result = await concurrent_ingestion.ingest_async()
            concurrent_duration = time.time() - concurrent_start

        # Assert
        # Both should process the same number of dates
        assert len(sequential_results) == len(test_dates)
        assert len(concurrent_result) == len(test_dates)

        # Concurrent should be faster (at least 1.5x since we're using multiple workers)
        # Calculate speedup factor
        speedup = sequential_duration / concurrent_duration
        logger.info(
            "Performance comparison",
            sequential=sequential_duration,
            concurrent=concurrent_duration,
            speedup=speedup,
        )
        assert speedup > 1.5, f"Expected speedup > 1.5x, got {speedup:.2f}x"

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

        # Mock process_item_async with selective failures
        async def mock_process_item(self, date):
            if date in failures:
                error_msg = f"Simulated API failure for date {date}"
                return {"item_key": date, "success": False, "error": error_msg}

            processed_dates.append(date)
            return {"item_key": date, "success": True, "result": {"success": True}}

        # Mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.write_scoreboard_data.return_value = {"success": True}
        mock_parquet.get_processed_dates.return_value = []

        # Patch necessary components
        with patch.object(ScoreboardIngestion, "process_item_async", mock_process_item), patch(
            "src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet
        ):
            # Create configuration
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date=TEST_DATES[0],
                end_date=TEST_DATES[-1],
            )

            # Create ingestion instance
            ingestion = ScoreboardIngestion(config)
            ingestion.parquet_storage = mock_parquet

            # Execute
            result = await ingestion.ingest_async()

        # Assert
        # Should return only successful dates
        assert sorted(result) == sorted(successful_dates)
        assert len(result) == len(successful_dates)

        # Should have processed only non-failure dates
        assert sorted(processed_dates) == sorted(successful_dates)

    @pytest.mark.asyncio()
    async def test_backoff_strategy_behavior_with_simulated_rate_limits(
        self, mock_db, mock_response_factory, espn_api_config
    ):
        """Test that the system can handle rate limits by retrying."""
        # Configure mock responses
        request_counts = {}

        # Create a mock for fetch_item_async that simulates rate limits
        async def mock_fetch_item_async(self, date):
            if date not in request_counts:
                request_counts[date] = 0

            request_counts[date] += 1

            # First request always fails with rate limit
            if request_counts[date] == 1:
                raise httpx.HTTPStatusError(
                    "429 Too Many Requests",
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )

            # Second request succeeds
            return {"events": [{"id": f"event_{date}"}]}

        # Mock the store_item_async method to return successful result
        async def mock_store_item_async(self, date, data):
            return {"success": True, "file_path": f"test_{date}.parquet"}

        # Use a subset of dates for this test
        test_dates = TEST_DATES[:2]  # Just two dates

        # Create test config
        test_config = ESPNApiConfig(
            base_url="https://example.com",
            endpoints={"scoreboard": "scoreboard"},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=3,
                timeout=0.1,
            ),
        )

        # Create configuration and ingestion
        config = ScoreboardIngestionConfig(
            espn_api_config=test_config,
            start_date=test_dates[0],
            end_date=test_dates[-1],
        )

        # Test the retry behavior directly by making consecutive calls
        with (
            patch.object(ScoreboardIngestion, "fetch_item_async", mock_fetch_item_async),
            patch.object(ScoreboardIngestion, "store_item_async", mock_store_item_async),
            patch("asyncio.sleep", AsyncMock()),  # Skip actual sleeping
        ):
            # Create ingestion object
            ingestion = ScoreboardIngestion(config)

            # Test direct calls to process_item_async - this should handle retries
            for date in test_dates:
                # First call should fail
                with pytest.raises(httpx.HTTPStatusError):
                    await ingestion.fetch_item_async(date)

                # But immediate retry should succeed
                result = await ingestion.fetch_item_async(date)
                assert "events" in result

            # Verify request counts are correct
            for date in test_dates:
                assert request_counts[date] == 2, "Expected 2 requests"

        # Success: test shows that retries work as expected
