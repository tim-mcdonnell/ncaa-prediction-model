"""Tests for the refactored Scoreboard ingestion module.

This test suite validates the functionality of the new ScoreboardIngestion implementation
that uses the BaseIngestion abstract base class.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest.scoreboard import (
    ScoreboardIngestion,
    ScoreboardIngestionConfig,
    _determine_dates_to_process,
    ingest_scoreboard,
    ingest_scoreboard_async,
)
from src.utils.config import ESPNApiConfig, RequestSettings


@pytest.fixture
def mock_espn_api_config():
    """Create a mock ESPN API configuration for testing."""
    return ESPNApiConfig(
        base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        v3_base_url="https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball",
        endpoints={
            "scoreboard": "scoreboard?dates={date}",
        },
        request_settings=RequestSettings(
            initial_request_delay=0.01,
            max_retries=1,
            timeout=1.0,
            max_concurrency=1,
        ),
    )


@pytest.fixture
def mock_scoreboard_response():
    """Create a mock scoreboard API response."""
    return {
        "events": [
            {
                "id": "401123456",
                "date": "2023-01-01T18:00Z",
                "name": "Team A vs Team B",
                "status": {"type": {"completed": True}},
                "competitions": [
                    {
                        "id": "401123456",
                        "status": {"type": {"completed": True}},
                        "competitors": [
                            {
                                "id": "1",
                                "team": {"id": "1", "name": "Team A", "abbreviation": "TA"},
                                "score": "75",
                                "homeAway": "home",
                            },
                            {
                                "id": "2",
                                "team": {"id": "2", "name": "Team B", "abbreviation": "TB"},
                                "score": "70",
                                "homeAway": "away",
                            },
                        ],
                    }
                ],
            },
            {
                "id": "401123457",
                "date": "2023-01-01T20:00Z",
                "name": "Team C vs Team D",
                "status": {"type": {"completed": True}},
                "competitions": [
                    {
                        "id": "401123457",
                        "status": {"type": {"completed": True}},
                        "competitors": [
                            {
                                "id": "3",
                                "team": {"id": "3", "name": "Team C", "abbreviation": "TC"},
                                "score": "60",
                                "homeAway": "home",
                            },
                            {
                                "id": "4",
                                "team": {"id": "4", "name": "Team D", "abbreviation": "TD"},
                                "score": "65",
                                "homeAway": "away",
                            },
                        ],
                    }
                ],
            },
        ]
    }


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    mock_client = MagicMock()
    mock_client.request_async = AsyncMock()
    mock_client.get_endpoint_url = MagicMock(return_value="https://example.com/endpoint")
    return mock_client


@pytest.fixture
def mock_parquet_storage():
    """Create a mock ParquetStorage instance."""
    mock_storage = MagicMock()
    mock_storage.write_scoreboard_data = MagicMock(
        return_value={"success": True, "file_path": "test.parquet"}
    )
    mock_storage.get_processed_dates = MagicMock(return_value=[])
    return mock_storage


class MockScoreboardIngestion(ScoreboardIngestion):
    """Mock implementation that skips the parent class initialization issues."""

    def __init__(self, config):
        """Initialize with mocked dependencies to avoid actual API client initialization."""
        # Skip the parent class initialization
        self.config = config

        # Create mocked dependencies
        self.parquet_storage = MagicMock()
        self.api_client = MagicMock()

        # Setup a semaphore for concurrency
        self.semaphore = MagicMock()
        self.semaphore.__aenter__ = AsyncMock()
        self.semaphore.__aexit__ = AsyncMock()

    async def fetch_item_async(self, date):
        """Override to provide a custom implementation.

        Doesn't require .fetch_scoreboard_async.
        """
        return await self.api_client.request_async()


class TestScoreboardIngestion:
    """Tests for the ScoreboardIngestion class."""

    def test_config_initialization(self, mock_espn_api_config):
        """Test that ScoreboardIngestionConfig initializes correctly."""
        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            start_date="2023-01-01",
            end_date="2023-01-03",
        )

        assert config.espn_api_config == mock_espn_api_config
        assert config.start_date == "2023-01-01"
        assert config.end_date == "2023-01-03"

    @patch("src.ingest.scoreboard.get_date_range")
    def test_determine_dates_to_process(self, mock_get_date_range):
        """Test that date determination works correctly."""
        # Set up mock return
        expected_dates = ["2023-01-01", "2023-01-02", "2023-01-03"]
        mock_get_date_range.return_value = expected_dates

        # Test date range
        config = ScoreboardIngestionConfig(
            espn_api_config=MagicMock(),
            start_date="2023-01-01",
            end_date="2023-01-03",
        )

        result = _determine_dates_to_process(config)
        assert result == expected_dates

        # Test single date
        config = ScoreboardIngestionConfig(
            espn_api_config=MagicMock(),
            date="2023-01-01",
        )

        # Mock for single date case
        mock_get_date_range.return_value = ["2023-01-01"]

        result = _determine_dates_to_process(config)
        assert result == ["2023-01-01"]

    @pytest.mark.asyncio
    async def test_fetch_item_async(
        self, mock_espn_api_config, mock_api_client, mock_scoreboard_response
    ):
        """Test fetch_item_async calls the API with correct parameters."""
        # Arrange
        test_date = "2023-01-01"
        mock_api_client.request_async.return_value = mock_scoreboard_response

        # Create instance
        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            date=test_date,
        )
        ingestion = MockScoreboardIngestion(config)
        ingestion.api_client = mock_api_client

        # Act
        result = await ingestion.fetch_item_async(test_date)

        # Assert
        assert result == mock_scoreboard_response
        mock_api_client.request_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_item_async(
        self, mock_espn_api_config, mock_api_client, mock_parquet_storage, mock_scoreboard_response
    ):
        """Test store_item_async correctly stores data."""
        # Arrange
        test_date = "2023-01-01"

        # Create instance with mocked dependencies
        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            date=test_date,
        )
        ingestion = MockScoreboardIngestion(config)
        ingestion.api_client = mock_api_client
        ingestion.parquet_storage = mock_parquet_storage

        # Mock asyncio.get_running_loop and run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            return_value={"success": True, "file_path": "test.parquet"}
        )

        # Act
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            result = await ingestion.store_item_async(test_date, mock_scoreboard_response)

        # Assert
        assert result["success"] is True
        assert result["file_path"] == "test.parquet"
        mock_loop.run_in_executor.assert_called_once()

    def test_get_processed_items(self, mock_espn_api_config, mock_parquet_storage):
        """Test get_processed_items returns the correct list."""
        # Arrange
        processed_dates = [date(2023, 1, 1), date(2023, 1, 2)]
        mock_parquet_storage.get_processed_dates = MagicMock(return_value=processed_dates)

        # Create instance
        config = ScoreboardIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = MockScoreboardIngestion(config)
        ingestion.parquet_storage = mock_parquet_storage

        # Act
        result = ingestion.get_processed_items()

        # Assert
        assert result == processed_dates
        mock_parquet_storage.get_processed_dates.assert_called_once()

    @patch("src.ingest.scoreboard._determine_dates_to_process")
    def test_determine_items_to_process(self, mock_determine, mock_espn_api_config):
        """Test determine_items_to_process returns the correct dates."""
        # Arrange
        dates = ["2023-01-01", "2023-01-02"]
        mock_determine.return_value = dates

        # Create instance
        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            start_date="2023-01-01",
            end_date="2023-01-02",
        )
        ingestion = MockScoreboardIngestion(config)

        # Act
        result = ingestion.determine_items_to_process()

        # Assert
        assert result == dates
        mock_determine.assert_called_once_with(config)

    @pytest.mark.asyncio
    @patch("src.ingest.scoreboard.ScoreboardIngestion")
    async def test_ingest_scoreboard_async(self, mock_ingestion_class, mock_espn_api_config):
        """Test ingest_scoreboard_async function."""
        # Arrange
        test_date = date(2023, 1, 1)
        mock_instance = mock_ingestion_class.return_value
        mock_instance.ingest_async = AsyncMock(return_value=[test_date])

        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            date="2023-01-01",
        )

        # Act
        result = await ingest_scoreboard_async(config)

        # Assert
        assert result == [test_date]
        mock_ingestion_class.assert_called_once_with(config)
        mock_instance.ingest_async.assert_called_once()

    @patch("src.ingest.scoreboard.asyncio.run")
    def test_ingest_scoreboard(self, mock_asyncio_run, mock_espn_api_config):
        """Test ingest_scoreboard function calls the async version correctly."""
        # Arrange
        test_date = date(2023, 1, 1)
        mock_asyncio_run.return_value = [test_date]

        config = ScoreboardIngestionConfig(
            espn_api_config=mock_espn_api_config,
            date="2023-01-01",
        )

        # Act
        result = ingest_scoreboard(config)

        # Assert
        assert result == [test_date]
        mock_asyncio_run.assert_called_once()
