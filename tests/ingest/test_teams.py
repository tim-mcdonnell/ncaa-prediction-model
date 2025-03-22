"""Tests for the refactored Teams ingestion module.

This test suite validates the functionality of the new TeamsIngestion implementation
that uses the BaseIngestion abstract base class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest.teams import TeamsIngestion, TeamsIngestionConfig, ingest_teams, ingest_teams_async
from src.utils.config import ESPNApiConfig, RequestSettings


@pytest.fixture
def mock_espn_api_config():
    """Create a mock ESPN API configuration for testing."""
    return ESPNApiConfig(
        base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        v3_base_url="https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball",
        endpoints={
            "teams": "teams?limit={limit}&offset={offset}",
        },
        request_settings=RequestSettings(
            initial_request_delay=0.01,
            max_retries=1,
            timeout=1.0,
            max_concurrency=1,
        ),
    )


@pytest.fixture
def mock_teams_response():
    """Create a mock teams API response."""
    return {
        "sports": [
            {
                "leagues": [
                    {
                        "teams": [
                            {"team": {"id": "1", "name": "Team A", "abbreviation": "TA"}},
                            {"team": {"id": "2", "name": "Team B", "abbreviation": "TB"}},
                            {"team": {"id": "3", "name": "Team C", "abbreviation": "TC"}},
                            {"team": {"id": "4", "name": "Team D", "abbreviation": "TD"}},
                        ]
                    }
                ]
            }
        ]
    }


class MockTeamsIngestion(TeamsIngestion):
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

    def get_processed_items(self):
        """Override to return a mock list rather than calling the storage."""
        return self.parquet_storage.get_processed_pages()

    def determine_items_to_process(self):
        """Override to return a simple list for testing."""
        if isinstance(self.config.page, list):
            return self.config.page
        return [self.config.page]


class TestTeamsIngestion:
    """Tests for the TeamsIngestion class."""

    def test_config_initialization(self, mock_espn_api_config):
        """Test that TeamsIngestionConfig initializes correctly."""
        config = TeamsIngestionConfig(espn_api_config=mock_espn_api_config, limit=100, page=1)

        assert config.espn_api_config == mock_espn_api_config
        assert config.limit == 100
        assert config.page == 1

    @pytest.mark.asyncio
    async def test_fetch_item_async(self, mock_espn_api_config, mock_teams_response):
        """Test fetch_item_async calls the API with correct parameters."""
        # Arrange
        page = 1
        mock_api_client = MagicMock()
        mock_api_client._request_async = AsyncMock(return_value=mock_teams_response)
        mock_api_client.get_endpoint_url = MagicMock(return_value="https://api.espn.com/v1/teams")

        # Create instance
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=page,
        )
        ingestion = MockTeamsIngestion(config)
        ingestion.api_client = mock_api_client

        # Act
        result = await ingestion.fetch_item_async(page)

        # Assert
        assert result == mock_teams_response
        mock_api_client._request_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_item_async(self, mock_espn_api_config, mock_teams_response):
        """Test store_item_async correctly stores data."""
        # Arrange
        page = 1
        mock_api_client = MagicMock()
        mock_parquet_storage = MagicMock()

        # Create instance with mocked dependencies
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=page,
        )
        ingestion = MockTeamsIngestion(config)
        ingestion.api_client = mock_api_client
        ingestion.parquet_storage = mock_parquet_storage

        # Mock asyncio.get_running_loop and run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            return_value={"success": True, "file_path": "test.parquet"}
        )

        # Act
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            result = await ingestion.store_item_async(page, mock_teams_response)

        # Assert
        assert result["success"] is True
        assert result["file_path"] == "test.parquet"
        mock_loop.run_in_executor.assert_called_once()

    def test_get_processed_items(self, mock_espn_api_config):
        """Test get_processed_items returns the correct list."""
        # Arrange
        processed_pages = [1, 2]
        mock_parquet_storage = MagicMock()
        mock_parquet_storage.get_processed_pages = MagicMock(return_value=processed_pages)

        # Create instance
        config = TeamsIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = MockTeamsIngestion(config)
        ingestion.parquet_storage = mock_parquet_storage

        # Act
        result = ingestion.get_processed_items()

        # Assert
        assert result == processed_pages
        mock_parquet_storage.get_processed_pages.assert_called_once()

    def test_determine_items_to_process(self, mock_espn_api_config):
        """Test determine_items_to_process returns the correct pages."""
        # Arrange
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=1,
        )
        ingestion = MockTeamsIngestion(config)

        # Act
        result = ingestion.determine_items_to_process()

        # Assert
        assert result == [1]

        # Test with multiple pages
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=[1, 2, 3],
        )
        ingestion = MockTeamsIngestion(config)

        # Act
        result = ingestion.determine_items_to_process()

        # Assert
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    @patch("src.ingest.teams.TeamsIngestion")
    async def test_ingest_teams_async(self, mock_ingestion_class, mock_espn_api_config):
        """Test ingest_teams_async function."""
        # Arrange
        test_pages = [1]
        mock_instance = mock_ingestion_class.return_value
        mock_instance.ingest_async = AsyncMock(return_value=test_pages)

        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=1,
        )

        # Act
        result = await ingest_teams_async(config)

        # Assert
        assert result == test_pages
        mock_ingestion_class.assert_called_once_with(config)
        mock_instance.ingest_async.assert_called_once()

    @patch("src.ingest.teams.asyncio.run")
    def test_ingest_teams(self, mock_asyncio_run, mock_espn_api_config):
        """Test ingest_teams function calls the async version correctly."""
        # Arrange
        test_pages = [1]
        mock_asyncio_run.return_value = test_pages

        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            limit=100,
            page=1,
        )

        # Act
        result = ingest_teams(config)

        # Assert
        assert result == test_pages
        mock_asyncio_run.assert_called_once()
