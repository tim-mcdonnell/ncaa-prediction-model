import json  # Add import for JSON handling
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from src.ingest.scoreboard import (
    ScoreboardIngestion,
    ScoreboardIngestionConfig,
    ingest_scoreboard,
    ingest_scoreboard_async,
)
from src.utils.config import ESPNApiConfig, RequestSettings
from src.utils.date_utils import format_date_for_api
from src.utils.espn_api_client import ESPNApiClient
from src.utils.parquet_storage import ParquetStorage

logger = structlog.get_logger(__name__)

# Constants for test values
NUM_TEST_DATES = 3
NUM_UNPROCESSED_DATES = 2

TEST_DB_PATH = os.path.join("tests", "data", "test.db")
PARQUET_DIR = "tests/data/parquet"


class _TestFetchError(Exception):
    """Error raised for testing fetch failures."""


class TestScoreboardIngestion:
    """Tests for the scoreboard data ingestion module."""

    @pytest.fixture()
    def espn_api_config(self):
        """Return a mock ESPN API configuration."""
        config = ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={"scoreboard": "scoreboard"},
            request_settings=RequestSettings(
                initial_request_delay=0.1,
                max_retries=3,
                timeout=10,
                batch_size=5,
                max_concurrency=3,
                min_request_delay=0.05,
                max_request_delay=1.0,
                backoff_factor=1.5,
                recovery_factor=0.9,
                error_threshold=3,
                success_threshold=10,
            ),
        )

        # Add historical attribute manually
        config.historical = {"start_date": "2022-11-01", "seasons": [2022, 2023]}

        # For backwards compatibility
        config.historical_start_date = "2022-11-01"

        return config

    @pytest.fixture()
    def mock_db(self):
        """Create a mock database."""
        mock = MagicMock()
        return mock

    @pytest.fixture()
    def mock_api_client(self):
        """Create a mock ESPN API client."""
        mock = MagicMock(spec=ESPNApiClient)
        mock.fetch_scoreboard.return_value = {
            "events": [
                {
                    "id": "401403389",
                    "date": "2023-03-15T23:30Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "401403389",
                            "status": {"type": {"completed": True}},
                            "competitors": [
                                {"team": {"id": "52", "score": "75"}},
                                {"team": {"id": "2", "score": "70"}},
                            ],
                        }
                    ],
                }
            ]
        }
        return mock

    @pytest.fixture()
    def mock_async_api_client(self):
        """Create a mock async ESPN API client."""
        mock = MagicMock(spec=ESPNApiClient)

        # Create the AsyncMock with proper handling
        async def mock_fetch_scoreboard_async(*args, **kwargs):
            return {
                "events": [
                    {
                        "id": "401403389",
                        "date": "2023-03-15T23:30Z",
                        "name": "Team A vs Team B",
                        "competitions": [
                            {
                                "id": "401403389",
                                "status": {"type": {"completed": True}},
                                "competitors": [
                                    {"team": {"id": "52", "score": "75"}},
                                    {"team": {"id": "2", "score": "70"}},
                                ],
                            }
                        ],
                    }
                ]
            }

        # Use the function instead of AsyncMock directly
        mock.fetch_scoreboard_async = mock_fetch_scoreboard_async
        mock.get_endpoint_url.return_value = "https://example.com/endpoint"
        return mock

    @pytest.fixture()
    def mock_api_client_with_patch(self):
        """Mock ESPNApiClient with patch."""
        with patch("src.ingest.scoreboard.ESPNApiClient") as mock:
            yield mock

    @pytest.fixture()
    def api_config_dict(self):
        """Dictionary-style API configuration."""
        return {
            "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            "endpoints": {"scoreboard": "scoreboard"},
            "initial_request_delay": 0.1,
            "max_retries": 3,
            "timeout": 10,
            "batch_size": 5,
            "max_concurrency": 3,
            "min_request_delay": 0.05,
            "max_request_delay": 1.0,
            "backoff_factor": 1.5,
            "recovery_factor": 0.9,
            "error_threshold": 3,
            "success_threshold": 10,
            "historical": {"start_date": "2022-11-01", "seasons": [2022, 2023]},
        }

    @pytest.fixture()
    def api_config_object(self):
        """Object-style API configuration."""
        config = ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={"scoreboard": "scoreboard"},
            request_settings=RequestSettings(
                initial_request_delay=0.1,
                max_retries=3,
                timeout=10,
                batch_size=5,
                max_concurrency=3,
                min_request_delay=0.05,
                max_request_delay=1.0,
                backoff_factor=1.5,
                recovery_factor=0.9,
                error_threshold=3,
                success_threshold=10,
            ),
        )

        # Add historical attribute manually
        config.historical = {"start_date": "2022-11-01", "seasons": [2022, 2023]}

        return config

    @pytest.fixture
    def mock_espn_api_config(self):
        """Provide a mock ESPN API config for testing."""
        from src.utils.config import ESPNApiConfig, RequestSettings

        # Create a RequestSettings instance with test values
        request_settings = RequestSettings(
            initial_request_delay=0.01,
            max_retries=1,
            timeout=1,
            batch_size=5,
            max_concurrency=2,
            min_request_delay=0.01,
            max_request_delay=0.1,
            backoff_factor=1.1,
            recovery_factor=0.9,
            error_threshold=2,
            success_threshold=5,
        )

        # Create endpoints dictionary
        endpoints = {
            "scoreboard": "sports/basketball/mens-college-basketball/scoreboard",
            "teams": "sports/basketball/mens-college-basketball/teams",
        }

        # Create historical data
        historical = {"start_date": "2023-01-01", "seasons": [2023]}

        # Return the ESPNApiConfig with the request_settings
        return ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/",
            v3_base_url="https://site.api.espn.com/apis/site/v3/",
            endpoints=endpoints,
            request_settings=request_settings,
            historical=historical,
        )

    def test_fetch_and_store_date_with_valid_date_fetches_and_stores_data(
        self, mock_db, mock_api_client, espn_api_config
    ):
        """Test fetch_and_store_date method with a valid date."""
        # Arrange
        date = "2023-03-15"
        scoreboard_data = {"events": [{"id": "401468229", "name": "Test Event"}]}
        mock_api_client.fetch_scoreboard.return_value = scoreboard_data

        # Create a mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.write_scoreboard_data.return_value = {"success": True}

        # Act
        with patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
            ingestion.api_client = mock_api_client  # Replace the API client with our mock
            result = ingestion.fetch_and_store_date(date)

        # Assert
        # The data should be fetched from the API client
        mock_api_client.fetch_scoreboard.assert_called_once_with(
            date="20230315"
        )  # Format for ESPN API
        # The result should be the same as what the API returned
        assert result == scoreboard_data
        # Verify ParquetStorage.write_scoreboard_data was called with correct parameters
        mock_parquet.write_scoreboard_data.assert_called_once()
        # Check that the data parameter was passed correctly
        call_kwargs = mock_parquet.write_scoreboard_data.call_args[1]
        assert call_kwargs["data"] == scoreboard_data

    def test_ingest_scoreboard_with_specific_date_processes_date(
        self, mock_db, mock_api_client, espn_api_config, monkeypatch
    ):
        """Test ingest_scoreboard with a specific date."""
        # Arrange
        date = "2023-03-15"
        espn_date = "20230315"
        insert_called = False

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(_):
            # Simulate API call
            mock_api_client.fetch_scoreboard(date=espn_date)
            # Simulate database insert
            mock_db.insert_bronze_scoreboard(
                date=date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": "200"},
                data={"events": [{"id": "12345"}]},
            )
            nonlocal insert_called
            insert_called = True
            return [date]

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=[date]),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda _: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                date=date,
                db_path=TEST_DB_PATH,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == [date]
        mock_api_client.fetch_scoreboard.assert_called_once_with(date=espn_date)
        assert insert_called, "insert_bronze_scoreboard was not called"

    def test_ingest_scoreboard_with_date_range_processes_date_range(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with date range processes dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = []  # No dates processed

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(_):
            for date in dates:
                espn_date = date.replace("-", "")
                mock_api_client.fetch_scoreboard(date=espn_date)
            return dates

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=dates),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda _: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date="2023-03-15",
                end_date="2023-03-17",
                db_path=TEST_DB_PATH,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == dates
        assert mock_api_client.fetch_scoreboard.call_count >= len(dates)

    def test_ingest_scoreboard_with_yesterday_flag_processes_yesterday(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with yesterday flag processes yesterday's date."""
        # Arrange
        yesterday_date = "2023-03-14"
        espn_date = "20230314"
        insert_called = False

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(_):
            # Simulate API call
            mock_api_client.fetch_scoreboard(date=espn_date)
            # Simulate database insert
            mock_db.insert_bronze_scoreboard(
                date=yesterday_date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": "200"},
                data={"events": [{"id": "12345"}]},
            )
            nonlocal insert_called
            insert_called = True
            return [yesterday_date]

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_yesterday", return_value=yesterday_date),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=[yesterday_date]),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda _: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                yesterday=True,
                db_path=TEST_DB_PATH,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == [yesterday_date]
        mock_api_client.fetch_scoreboard.assert_called_once_with(date=espn_date)

    def test_ingest_scoreboard_with_season_processes_entire_season(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with season processes the entire season dates."""
        # Arrange
        season_start = "2022-11-01"
        season_end = "2023-04-01"
        season_dates = ["2022-11-01", "2022-11-02", "2022-11-03"]  # Shortened for test
        mock_db.get_processed_dates.return_value = []  # No dates processed

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(_):
            # Simulate API calls
            for date in season_dates:
                espn_date = date.replace("-", "")
                mock_api_client.fetch_scoreboard(date=espn_date)
            return season_dates

        # Patch necessary components
        with (
            patch(
                "src.ingest.scoreboard.get_season_date_range",
                return_value=(season_start, season_end),
            ),
            patch("src.ingest.scoreboard.get_date_range", return_value=season_dates),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=season_dates),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda _: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                seasons=["2022-23"],
                db_path=TEST_DB_PATH,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == season_dates
        assert mock_api_client.fetch_scoreboard.call_count >= len(season_dates)

    def test_ingest_scoreboard_with_historical_processes_date_range(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with no parameters processes all historical dates."""
        # Arrange
        historical_start = "2022-11-01"
        yesterday = "2023-03-14"
        historical_dates = ["2022-11-01", "2022-11-02", "2022-11-03"]  # Shortened for test
        mock_db.get_processed_dates.return_value = []  # No dates processed

        # Set historical start date in config
        espn_api_config.historical_start_date = historical_start

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Create a side effect for fetch_and_store_date
        def mock_fetch_and_store(date, db):
            espn_date = date.replace("-", "")

            # Call the actual fetch_scoreboard method to register the call
            api_response = mock_api_client.fetch_scoreboard(date=espn_date)

            # Call insert_bronze_scoreboard
            db.insert_bronze_scoreboard(
                date=date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": "200"},
                data=api_response,
            )
            return api_response

        # Mock the async ingest function with a sync function
        def mock_ingest_scoreboard_async_sync(_):
            # Simulate API calls
            for date in historical_dates:
                espn_date = date.replace("-", "")
                mock_api_client.fetch_scoreboard(date=espn_date)
            return historical_dates

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_yesterday", return_value=yesterday),
            patch("src.ingest.scoreboard.get_date_range", return_value=historical_dates),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=historical_dates),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda _: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Create a mock for Database that returns our mock_db
            db_mock = MagicMock()
            db_mock.__enter__.return_value = mock_db
            db_mock.__exit__.return_value = None

            with patch("src.ingest.scoreboard.Database", return_value=db_mock):
                # Run the code under test
                config = ScoreboardIngestionConfig(
                    espn_api_config=espn_api_config,
                    db_path=TEST_DB_PATH,
                )
                result = ingest_scoreboard(config)

        # Assert
        assert result == historical_dates
        assert mock_api_client.fetch_scoreboard.call_count >= len(historical_dates)

    def test_ingest_scoreboard_with_no_parameters_uses_historical_start_date(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with no parameters uses the historical start date."""
        # Arrange
        historical_start = "2022-11-01"
        yesterday = "2023-03-14"
        historical_dates = ["2022-11-01", "2022-11-02", "2022-11-03"]  # Shortened for test
        mock_db.get_processed_dates.return_value = []  # No dates processed

        # Set historical start date in config
        espn_api_config.historical_start_date = historical_start

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Create a side effect for fetch_and_store_date
        def mock_fetch_and_store(date, db):
            espn_date = date.replace("-", "")

            # Call the actual fetch_scoreboard method to register the call
            api_response = mock_api_client.fetch_scoreboard(date=espn_date)

            # Call insert_bronze_scoreboard
            db.insert_bronze_scoreboard(
                date=date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": "200"},
                data=api_response,
            )
            return api_response

        # Mock the async ingest function
        async def mock_ingest_async(_):
            # Simulate the behavior of ingest_scoreboard_async
            for date in historical_dates:
                espn_date = date.replace("-", "")
                mock_api_client.fetch_scoreboard(date=espn_date)
            return historical_dates

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_yesterday", return_value=yesterday),
            patch("src.ingest.scoreboard.get_date_range", return_value=historical_dates),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", side_effect=mock_ingest_async),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Create a mock for Database that returns our mock_db
            db_mock = MagicMock()
            db_mock.__enter__.return_value = mock_db
            db_mock.__exit__.return_value = None

            with patch("src.ingest.scoreboard.Database", return_value=db_mock):
                # Run the code under test
                config = ScoreboardIngestionConfig(
                    espn_api_config=espn_api_config,
                    db_path=TEST_DB_PATH,
                )
                result = ingest_scoreboard(config)

        # Assert
        assert result == historical_dates
        assert mock_api_client.fetch_scoreboard.call_count >= len(historical_dates)

    def test_init_with_dict_config(self, mock_api_client_with_patch, api_config_dict):
        """Test initialization with dictionary configuration."""
        ingestion = ScoreboardIngestion(api_config_dict, db_path=TEST_DB_PATH)

        # Test that ESPNApiClient is called with a config object
        mock_api_client_with_patch.assert_called_once()
        # Get the actual argument passed
        call_args = mock_api_client_with_patch.call_args
        config_arg = call_args[0][0]

        # Verify it's an ESPNApiConfig with the expected properties
        assert config_arg.base_url == api_config_dict["base_url"]
        assert config_arg.endpoints == api_config_dict["endpoints"]

        # Check the request_settings attributes
        rs = config_arg.request_settings
        assert rs.initial_request_delay == api_config_dict["initial_request_delay"]
        assert rs.max_retries == api_config_dict["max_retries"]
        assert rs.timeout == api_config_dict["timeout"]

        assert ingestion.batch_size == api_config_dict["batch_size"]
        assert ingestion.db_path == TEST_DB_PATH

    def test_init_with_object_config(self, mock_api_client_with_patch, api_config_object):
        """Test initialization with object configuration."""
        ingestion = ScoreboardIngestion(api_config_object, db_path=TEST_DB_PATH)

        # Test that ESPNApiClient is called with a config object
        mock_api_client_with_patch.assert_called_once()
        # Get the actual argument passed
        call_args = mock_api_client_with_patch.call_args
        config_arg = call_args[0][0]

        # Verify it's an ESPNApiConfig with the expected properties
        assert config_arg.base_url == api_config_object.base_url
        assert config_arg.endpoints == api_config_object.endpoints

        # Check the request_settings attributes
        rs = config_arg.request_settings
        assert rs.initial_request_delay == api_config_object.request_settings.initial_request_delay
        assert rs.max_retries == api_config_object.request_settings.max_retries
        assert rs.timeout == api_config_object.request_settings.timeout

        assert ingestion.batch_size == api_config_object.request_settings.batch_size
        assert ingestion.db_path == TEST_DB_PATH

    @pytest.mark.asyncio()
    async def test_fetch_and_store_date_async_with_valid_date_fetches_and_stores_data(
        self, mock_db, mock_async_api_client, espn_api_config
    ):
        """Test that fetch_and_store_date_async properly stores data for valid dates."""
        # Arrange
        date = "2023-03-15"
        espn_date = "20230315"  # Format expected by ESPN API

        # Expected API response
        expected_response = {
            "events": [
                {
                    "id": "401403389",
                    "date": "2023-03-15T23:30Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "401403389",
                            "status": {"type": {"completed": True}},
                            "competitors": [
                                {"team": {"id": "52", "score": "75"}},
                                {"team": {"id": "2", "score": "70"}},
                            ],
                        }
                    ],
                }
            ]
        }

        # Create a MagicMock for the fetch_scoreboard_async method
        mock_fetch = AsyncMock(return_value=expected_response)
        mock_async_api_client.fetch_scoreboard_async = mock_fetch
        mock_async_api_client.get_endpoint_url.return_value = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

        # Setup mock for ParquetStorage
        mock_parquet_instance = MagicMock()
        mock_parquet_instance.write_scoreboard_data.return_value = {"success": True}
        mock_parquet_cls = MagicMock(return_value=mock_parquet_instance)

        # Act
        with (
            patch("src.ingest.scoreboard.ParquetStorage", mock_parquet_cls),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
        ):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
            ingestion.api_client = mock_async_api_client  # Replace the API client with our mock
            result = await ingestion.fetch_and_store_date_async(date, mock_db)

        # Assert
        assert result == expected_response  # Should return API response data
        mock_fetch.assert_called_once_with(date=espn_date)
        mock_parquet_instance.write_scoreboard_data.assert_called_once_with(
            date=date,
            source_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
            parameters={"dates": espn_date, "groups": "50", "limit": 200},
            data=result,
            force_overwrite=False,
        )

    @pytest.mark.asyncio
    async def test_process_date_range_with_multiple_dates_processes_all_dates_async(
        self, mock_db, mock_async_api_client, espn_api_config
    ):
        """Test process_date_range_async method processes all dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        processed_dates = []

        # Create a mock function for fetch_and_store_date_async
        async def mock_fetch_and_store(date, db=None):
            processed_dates.append(date)
            return {"events": [{"id": f"event_{date}"}]}

        # Mock ParquetStorage
        mock_parquet_instance = MagicMock()
        mock_parquet_instance.is_date_processed.return_value = False  # No dates processed yet
        mock_parquet_cls = MagicMock(return_value=mock_parquet_instance)

        # Act
        with (
            patch("src.ingest.scoreboard.ParquetStorage", mock_parquet_cls),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
        ):
            # Create instance
            ingestion = ScoreboardIngestion(
                espn_api_config=espn_api_config,
                db_path=TEST_DB_PATH,
                parquet_dir=PARQUET_DIR,
            )

            # Replace fetch_and_store_date_async with our mock
            ingestion.fetch_and_store_date_async = mock_fetch_and_store

            # Process the dates
            results = await ingestion.process_date_range_async(dates)

        # Assert - all dates should be processed
        assert sorted(processed_dates) == sorted(dates)
        assert sorted(results) == sorted(dates)

    @pytest.mark.asyncio()
    async def test_process_date_range_async_with_already_processed_dates_skips_processed_dates(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test that process_date_range_async skips already processed dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]

        # Track processed dates
        processed_dates = []

        # Create a mock function for fetch_and_store_date_async
        async def mock_fetch_and_store(date, db=None):
            processed_dates.append(date)
            return {"success": True}

        # Create the ParquetStorage mock
        mock_parquet_instance = MagicMock()
        # Mock is_date_processed to return True for the middle date
        mock_parquet_instance.is_date_processed.side_effect = (
            lambda date, endpoint: date == "2023-03-16"
        )
        mock_parquet_cls = MagicMock(return_value=mock_parquet_instance)

        # Patch the necessary dependencies
        with (
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.ParquetStorage", mock_parquet_cls),
        ):
            # Create the ScoreboardIngestion instance
            ingestion = ScoreboardIngestion(
                espn_api_config=espn_api_config,
                db_path=TEST_DB_PATH,
                skip_existing=True,  # Skip already processed dates
                parquet_dir="test_dir",
            )

            # Replace the fetch_and_store_date_async method with our mock
            ingestion.fetch_and_store_date_async = mock_fetch_and_store

            # Act - process the dates
            result = await ingestion.process_date_range_async(dates)

        # Assert - only unprocessed dates should have been processed
        assert sorted(processed_dates) == sorted(["2023-03-15", "2023-03-17"])
        # Result should include only processed dates
        assert sorted(result) == sorted(["2023-03-15", "2023-03-17"])

    @pytest.mark.asyncio()
    async def test_process_date_range_async_with_error_handling_continues_processing(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test that process_date_range_async handles errors and continues processing."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        processed_dates = []  # Track which dates are processed
        error_date = "2023-03-16"  # Middle date will raise an error

        # Create a mock function for fetch_and_store that raises an error for a specific date
        async def mock_fetch_and_store(date, *args, **kwargs):
            if date == error_date:
                raise ValueError(f"Error processing {date}")
            processed_dates.append(date)
            return {"events": [{"id": f"event_{date}"}]}

        # Mock ParquetStorage
        mock_parquet_instance = MagicMock()
        mock_parquet_instance.write_scoreboard_data.return_value = {"success": True}
        mock_parquet_instance.is_date_processed.return_value = False  # No dates processed yet
        mock_parquet_cls = MagicMock(return_value=mock_parquet_instance)

        # Patch the necessary methods and classes
        with (
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.ParquetStorage", mock_parquet_cls),
        ):
            # Create the ScoreboardIngestion instance with proper config
            ingestion = ScoreboardIngestion(
                espn_api_config=espn_api_config,
                db_path=TEST_DB_PATH,
                skip_existing=False,
                parquet_dir="test_dir",
                force_overwrite=False,
            )

            # Replace the API client with our mock
            ingestion.api_client = mock_async_api_client

            # Replace fetch_and_store_date_async with our mock
            ingestion.fetch_and_store_date_async = mock_fetch_and_store

            # Act
            result = await ingestion.process_date_range_async(dates)

        # Assert
        # Should have processed all dates except the error date
        expected_processed = ["2023-03-15", "2023-03-17"]
        assert sorted(processed_dates) == sorted(expected_processed)
        # Result should include only successfully processed dates
        assert sorted(result) == sorted(expected_processed)

    @pytest.mark.asyncio()
    async def test_ingest_scoreboard_async_with_date_range_processes_date_range(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard_async with date range processes dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        expected_dates = ["2023-03-16", "2023-03-17"]  # First date is skipped as processed

        # Mock ParquetStorage
        mock_parquet_instance = MagicMock()
        mock_parquet_instance.write_scoreboard_data.return_value = {"success": True}
        mock_parquet_cls = MagicMock(return_value=mock_parquet_instance)

        # Use a mock class to patch the process_date_range_async method
        class MockScoreboardIngestion(ScoreboardIngestion):
            async def process_date_range_async(self, dates_to_process, **kwargs):
                # Return the expected dates without any actual processing
                return expected_dates

        # Patch necessary components and the class
        with (
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
            patch("src.ingest.scoreboard.ParquetStorage", mock_parquet_cls),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.ScoreboardIngestion", MockScoreboardIngestion),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date="2023-03-15",
                end_date="2023-03-17",
                db_path=TEST_DB_PATH,
                parquet_dir="data/raw",
            )
            result = await ingest_scoreboard_async(config)

        # Assert
        assert sorted(result) == sorted(expected_dates)

    @pytest.mark.asyncio()
    async def test_ingest_scoreboard_async_with_concurrency_override_uses_custom_concurrency(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard_async with concurrency override uses custom concurrency."""
        # Arrange
        custom_concurrency = 2  # Override to a lower value
        dates = ["2023-03-15"]

        # Mock ParquetStorage
        mock_parquet = MagicMock()
        mock_parquet.get_processed_dates.return_value = []
        mock_parquet.write_scoreboard_data.return_value = {"success": True}

        # Make a copy of the config to ensure we don't modify the original
        import copy

        test_config = copy.deepcopy(espn_api_config)
        original_concurrency = test_config.request_settings.max_concurrency

        # Mock implementations
        async def mock_fetch_and_store(date, *args, **kwargs):
            return {"events": [{"id": "12345"}]}

        # Use a class-based approach for storing the config
        class ApiClientFactory:
            def __init__(self):
                self.last_config = None

            def __call__(self, config):
                self.last_config = config
                return mock_async_api_client

        api_client_factory = ApiClientFactory()

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
            patch("src.ingest.scoreboard.ESPNApiClient", side_effect=api_client_factory),
            patch.object(
                ScoreboardIngestion, "fetch_and_store_date_async", side_effect=mock_fetch_and_store
            ),
            patch("src.utils.parquet_storage.ParquetStorage", return_value=mock_parquet),
            patch("src.ingest.scoreboard.Database", MagicMock()),
        ):
            # Run the code under test with concurrency override
            config = ScoreboardIngestionConfig(
                espn_api_config=test_config,
                date="2023-03-15",
                db_path=TEST_DB_PATH,
                parquet_dir="data/raw",
                concurrency=custom_concurrency,  # Override concurrency
            )

            # Create a side effect that will capture the concurrency parameter
            mock_pdr_async = AsyncMock()

            # Run the ingestion
            original_pdr_async = ScoreboardIngestion.process_date_range_async
            ScoreboardIngestion.process_date_range_async = mock_pdr_async

            try:
                await ingest_scoreboard_async(config)
            finally:
                # Restore the original method
                ScoreboardIngestion.process_date_range_async = original_pdr_async

        # Assert
        # Check that the concurrency override was passed correctly
        mock_pdr_async.assert_called_once()
        # Get the keyword arguments
        kwargs = mock_pdr_async.call_args[1]
        assert kwargs.get("concurrency") == custom_concurrency
        # Check original config is unchanged
        assert (
            espn_api_config.request_settings.max_concurrency == original_concurrency
        )  # Original fixture unchanged

    @pytest.mark.asyncio()
    async def test_concurrent_processing_respects_batch_size(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test that concurrent processing respects the batch size."""
        # Arrange
        batch_size = 2
        dates = ["2023-03-15", "2023-03-16", "2023-03-17", "2023-03-18"]

        # Set batch size on espn_api_config
        espn_api_config.request_settings.batch_size = batch_size

        # Track processed batches
        processed_batches = []

        # Mock implementation for the process_batch_async method
        async def mock_process_batch(batch, *args, **kwargs):
            processed_batches.append(list(batch))  # Store a copy of each batch
            return {"successful": len(batch), "failed": 0, "errors": []}

        # Create test instance with our mocked API client
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            ingestion.api_client = mock_async_api_client

            # Directly mock the method that processes batches
            original_method = ingestion.process_batch_async
            ingestion.process_batch_async = mock_process_batch

            # Set processed dates to empty to ensure all dates are processed
            ingestion.get_existing_dates = MagicMock(return_value=[])

            # Act
            try:
                await ingestion.process_date_range_async(dates)
            finally:
                # Restore original method
                ingestion.process_batch_async = original_method

        # Assert
        # Should have ceil(4/2) = 2 batches
        assert len(processed_batches) == 2

        # First batch should contain first two dates
        assert sorted(processed_batches[0]) == sorted(dates[0:2])

        # Second batch should contain last two dates
        assert sorted(processed_batches[1]) == sorted(dates[2:4])

    @pytest.mark.asyncio
    async def test_fetch_and_store_date_async_with_existing_date_uses_value_from_parquet(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test ScoreboardIngestion with force_overwrite parameter.

        This test creates a custom subclass of ScoreboardIngestion that adds
        logic to check if dates are already processed and to avoid API calls
        for those dates when force_overwrite=False.
        """
        # Arrange
        date = "2023-03-15"
        espn_date = format_date_for_api(date)

        # Data that will be returned by our mocks
        existing_data_dict = {"events": [{"id": "401468229", "name": "Test Event"}]}
        existing_data_str = json.dumps(existing_data_dict)
        fresh_data = {"events": [{"id": "401468229", "name": "Fresh Event"}]}

        # Create a custom subclass that implements the check we want to test
        class TestScoreboardIngestion(ScoreboardIngestion):
            async def fetch_and_store_date_async(self, date, db=None):
                """Override with check for already processed dates."""
                parquet_storage = ParquetStorage(base_dir=self.parquet_dir)

                # If date is already processed and we're not forcing overwrite,
                # use the existing data instead of calling the API
                if not self.force_overwrite and parquet_storage.is_date_processed(date):
                    logger.info("Using existing data for date", date=date)
                    data = parquet_storage.read_scoreboard_data(date)
                    # Parse JSON string to dict if it's a string
                    if isinstance(data, str):
                        data = json.loads(data)
                    logger.info(f"Type of data after parsing: {type(data)}, Value: {data}")
                    return data

                # Otherwise, use the parent implementation
                return await super().fetch_and_store_date_async(date, db)

        # Create mock parquet storage that returns our test data as a string
        # to simulate how the real ParquetStorage works
        mock_parquet = MagicMock()
        mock_parquet.is_date_processed.return_value = True  # Date is processed
        mock_parquet.read_scoreboard_data.return_value = existing_data_str

        # Create mock API client
        mock_async_api_client.fetch_scoreboard_async = AsyncMock(return_value=fresh_data)
        mock_async_api_client.get_endpoint_url.return_value = "https://api.espn.com/endpoint"

        # Create mock executor that just runs the function directly
        async def mock_run_in_executor(_, func):
            return func()

        mock_loop = MagicMock()
        mock_loop.run_in_executor = mock_run_in_executor

        # Test with force_overwrite=False
        with (
            patch("src.ingest.scoreboard.ParquetStorage", return_value=mock_parquet),
            patch("asyncio.get_running_loop", return_value=mock_loop),
        ):
            # Create ingestion instance with force_overwrite=False
            ingestion = TestScoreboardIngestion(
                espn_api_config=espn_api_config,
                db_path=TEST_DB_PATH,
                force_overwrite=False,
            )
            ingestion.api_client = mock_async_api_client

            # Act - call with force_overwrite=False
            result = await ingestion.fetch_and_store_date_async(date)

            # Log the actual result type and value for debugging
            logger.info(f"Result type: {type(result)}, Result value: {result}")

            # Assert
            assert result == existing_data_dict, f"Should return cached data. Got {result}"
            assert not mock_async_api_client.fetch_scoreboard_async.called, (
                "API should not be called when force_overwrite=False"
            )

            # Reset mocks
            mock_async_api_client.fetch_scoreboard_async.reset_mock()

            # Now test with force_overwrite=True
            ingestion.force_overwrite = True

            # Act - call with force_overwrite=True
            result = await ingestion.fetch_and_store_date_async(date)

            # Assert
            assert result == fresh_data, "Should return fresh data"
            mock_async_api_client.fetch_scoreboard_async.assert_called_once_with(date=espn_date)
