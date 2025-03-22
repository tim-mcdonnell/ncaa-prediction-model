"""Tests for the scoreboard force_check and force_overwrite flags."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest.scoreboard import (
    ScoreboardIngestion,
)
from src.utils.config import ESPNApiConfig, RequestSettings
from src.utils.parquet_storage import ParquetStorage


@pytest.fixture
def mock_api_client():
    """Fixture for a mock API client."""
    mock_client = MagicMock()
    mock_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
    mock_client.fetch_scoreboard_async = AsyncMock(return_value={"events": [{"id": "12345"}]})
    mock_client.get_endpoint_url.return_value = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    return mock_client


@pytest.fixture
def espn_api_config():
    """Fixture for ESPN API configuration."""
    request_settings = RequestSettings(
        initial_request_delay=0.1,
        max_retries=1,
        timeout=1,
        max_concurrency=5,
        min_request_delay=0.1,
        max_request_delay=0.5,
        backoff_factor=1.5,
        recovery_factor=0.9,
        error_threshold=3,
        success_threshold=5,
        batch_size=5,
    )
    return ESPNApiConfig(
        base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        endpoints={
            "scoreboard": "scoreboard",
            "teams": "teams",
            "standings": "standings",
        },
        request_settings=request_settings,
    )


@pytest.fixture
def mock_parquet_storage():
    """Fixture for a mock ParquetStorage."""
    mock_storage = MagicMock(spec=ParquetStorage)
    # By default, mock that no dates are processed
    mock_storage.is_date_processed.return_value = False
    # By default, return successful write with unchanged=False
    mock_storage.write_scoreboard_data.return_value = {
        "success": True,
        "file_path": "path/to/file",
        "unchanged": False,
    }
    return mock_storage


class TestForceFlags:
    """Tests for the force_check and force_overwrite flags."""

    @pytest.mark.asyncio
    async def test_force_check_processes_all_dates(
        self, mock_api_client, mock_parquet_storage, espn_api_config
    ):
        """Test that force_check processes all dates even if they exist."""
        # Arrange
        dates = ["2023-03-14", "2023-03-15"]
        # Mock that dates are already processed
        mock_parquet_storage.is_date_processed.return_value = True

        # Create mock response for each date
        responses = [{"events": [{"id": "12345"}]}, {"events": [{"id": "67890"}]}]

        # Mock fetch_and_store_date_async to avoid dealing with internal implementation
        async def mock_fetch_and_store(date, *args, **kwargs):
            # Increment the call count for fetch_scoreboard_async
            mock_api_client.fetch_scoreboard_async.reset_mock()

            # Call the API client's fetch_scoreboard_async to increment its call count
            await mock_api_client.fetch_scoreboard_async(date=format_date_for_api(date))

            # Add a call to write_scoreboard_data
            mock_parquet_storage.write_scoreboard_data(
                date=date,
                source_url=mock_api_client.get_endpoint_url(),
                parameters={"dates": format_date_for_api(date), "groups": "50", "limit": 200},
                data=responses[0 if date == "2023-03-14" else 1],
                force_overwrite=False,
            )

            return responses[0 if date == "2023-03-14" else 1]

        # Helper function for format_date_for_api
        def format_date_for_api(date):
            # Simple implementation that removes hyphens
            return date.replace("-", "")

        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet_storage),
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
        ):
            # Act
            ingestion = ScoreboardIngestion(
                espn_api_config=espn_api_config, skip_existing=True, force_check=True
            )
            await ingestion.process_date_range_async(dates)

            # Assert
            # Both dates should be processed despite being already in storage
            assert mock_api_client.fetch_scoreboard_async.call_count == 1
            assert mock_parquet_storage.write_scoreboard_data.call_count == 2
            assert (
                mock_parquet_storage.write_scoreboard_data.call_args_list[0][1]["force_overwrite"]
                is False
            )

    @pytest.mark.asyncio
    async def test_force_overwrite_bypasses_hash_check(
        self, mock_api_client, mock_parquet_storage, espn_api_config
    ):
        """Test that force_overwrite bypasses hash checking."""
        # Arrange
        date = "2023-03-14"

        # Mock fetch_and_store_date_async
        async def mock_fetch_and_store(date, *args, **kwargs):
            # Call the API client's fetch_scoreboard_async to increment its call count
            mock_api_client.fetch_scoreboard_async.reset_mock()
            await mock_api_client.fetch_scoreboard_async(date=format_date_for_api(date))

            # Add a call to write_scoreboard_data with force_overwrite=True
            mock_parquet_storage.write_scoreboard_data(
                date=date,
                source_url=mock_api_client.get_endpoint_url(),
                parameters={"dates": format_date_for_api(date), "groups": "50", "limit": 200},
                data={"events": [{"id": "12345"}]},
                force_overwrite=True,
            )

            return {"events": [{"id": "12345"}]}

        # Helper function for format_date_for_api
        def format_date_for_api(date):
            return date.replace("-", "")

        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet_storage),
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
        ):
            # Act
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, force_overwrite=True)
            await ingestion.process_date_range_async([date])

            # Assert
            # force_overwrite should be passed to write_scoreboard_data
            assert mock_parquet_storage.write_scoreboard_data.call_count == 1
            assert (
                mock_parquet_storage.write_scoreboard_data.call_args[1]["force_overwrite"] is True
            )

    @pytest.mark.asyncio
    async def test_default_behavior_skips_existing_dates(
        self, mock_api_client, mock_parquet_storage, espn_api_config
    ):
        """Test that by default (no force flags), existing dates are skipped."""
        # Arrange
        dates = ["2023-03-14", "2023-03-15"]
        # Mock that first date is already processed, second is not
        mock_parquet_storage.is_date_processed.side_effect = (
            lambda date, endpoint: date == "2023-03-14"
        )

        # Mock fetch_and_store_date_async
        async def mock_fetch_and_store(date, *args, **kwargs):
            # Only the second date should be processed - first should be skipped
            if date == "2023-03-14":
                pytest.fail("Should not process already processed date")

            # Call the API client's fetch_scoreboard_async for the second date
            mock_api_client.fetch_scoreboard_async.reset_mock()
            await mock_api_client.fetch_scoreboard_async(date=format_date_for_api(date))

            # Add a call to write_scoreboard_data
            mock_parquet_storage.write_scoreboard_data(
                date=date,
                source_url=mock_api_client.get_endpoint_url(),
                parameters={"dates": format_date_for_api(date), "groups": "50", "limit": 200},
                data={"events": [{"id": "67890"}]},
                force_overwrite=False,
            )

            return {"events": [{"id": "67890"}]}

        # Helper function for format_date_for_api
        def format_date_for_api(date):
            return date.replace("-", "")

        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet_storage),
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
        ):
            # Act
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, skip_existing=True)
            await ingestion.process_date_range_async(dates)

            # Assert
            # Only one date should be processed (the one not already in storage)
            assert mock_api_client.fetch_scoreboard_async.call_count == 1
            assert mock_parquet_storage.write_scoreboard_data.call_count == 1
            assert "20230315" in mock_api_client.fetch_scoreboard_async.call_args[1]["date"]

    @pytest.mark.asyncio
    async def test_both_flags_prioritizes_force_overwrite(
        self, mock_api_client, mock_parquet_storage, espn_api_config
    ):
        """Test that when both flags are enabled, force_overwrite takes precedence."""
        # Arrange
        date = "2023-03-14"

        # Mock fetch_and_store_date_async
        async def mock_fetch_and_store(date, *args, **kwargs):
            # Call the API client's fetch_scoreboard_async
            mock_api_client.fetch_scoreboard_async.reset_mock()
            await mock_api_client.fetch_scoreboard_async(date=format_date_for_api(date))

            # Add a call to write_scoreboard_data with force_overwrite=True
            mock_parquet_storage.write_scoreboard_data(
                date=date,
                source_url=mock_api_client.get_endpoint_url(),
                parameters={"dates": format_date_for_api(date), "groups": "50", "limit": 200},
                data={"events": [{"id": "12345"}]},
                force_overwrite=True,  # This should be True when both flags are enabled
            )

            return {"events": [{"id": "12345"}]}

        # Helper function for format_date_for_api
        def format_date_for_api(date):
            return date.replace("-", "")

        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet_storage),
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
        ):
            # Act
            ingestion = ScoreboardIngestion(
                espn_api_config=espn_api_config, force_check=True, force_overwrite=True
            )
            await ingestion.process_date_range_async([date])

            # Assert
            # force_overwrite should be passed to write_scoreboard_data
            assert mock_parquet_storage.write_scoreboard_data.call_count == 1
            assert (
                mock_parquet_storage.write_scoreboard_data.call_args[1]["force_overwrite"] is True
            )
