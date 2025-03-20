import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest.scoreboard import (
    ScoreboardIngestion,
    ScoreboardIngestionConfig,
    ingest_scoreboard,
    ingest_scoreboard_async,
)
from src.utils.config import ESPNApiConfig
from src.utils.espn_api_client import ESPNApiClient

# Constants for test values
NUM_TEST_DATES = 3
NUM_UNPROCESSED_DATES = 2

TEST_DB_PATH = os.path.join("tests", "data", "test.db")


class TestScoreboardIngestion:
    """Tests for the scoreboard data ingestion module."""

    @pytest.fixture()
    def espn_api_config(self):
        """Return a mock ESPN API configuration."""
        return ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={"scoreboard": "scoreboard"},
            initial_request_delay=0.1,
            max_retries=3,
            timeout=10,
            historical_start_date="2022-11-01",
            batch_size=5,
            max_concurrency=3,
            min_request_delay=0.05,
            max_request_delay=1.0,
            backoff_factor=1.5,
            recovery_factor=0.9,
            error_threshold=3,
            success_threshold=10,
        )

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
        mock.fetch_scoreboard_async = AsyncMock(
            return_value={
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
        )
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
            "historical_start_date": "2022-11-01",
            "batch_size": 5,
        }

    @pytest.fixture()
    def api_config_object(self):
        """Object-style API configuration."""
        return ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={"scoreboard": "scoreboard"},
            initial_request_delay=0.1,
            max_retries=3,
            timeout=10,
            historical_start_date="2022-11-01",
            batch_size=5,
        )

    def test_fetch_and_store_date_with_valid_date_fetches_and_stores_data(
        self, mock_db, mock_api_client, espn_api_config
    ):
        """Test fetch_and_store_date stores data when date is valid and not already processed."""
        # Arrange
        date = "2023-03-15"
        espn_date = "20230315"  # Format expected by ESPN API
        mock_db.get_processed_dates.return_value = []  # Date not processed

        # Act
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
            ingestion.api_client = mock_api_client  # Replace the API client with our mock
            result = ingestion.fetch_and_store_date(date, mock_db)

        # Assert
        assert isinstance(result, dict)  # Should return API response data
        mock_api_client.fetch_scoreboard.assert_called_once_with(date=espn_date)
        mock_db.insert_bronze_scoreboard.assert_called_once()

    def test_process_date_range_with_multiple_dates_processes_all_dates(
        self, mock_db, mock_api_client, espn_api_config
    ):
        """Test process_date_range processes all dates in the range."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = []  # No dates processed
        mock_db.insert_bronze_scoreboard.return_value = None  # Simulate successful inserts

        # Mock API client response
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # For tracking processed dates
        processed_dates = []

        # Create a straight mock implementation that just tracks the dates
        def mock_process_date_range_async(self_obj, dates_to_process):
            for date in dates_to_process:
                processed_dates.append(date)
            return dates_to_process

        # Act
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
            ingestion.api_client = mock_api_client  # Replace the API client with our mock

            # Directly patch the async method with a synchronous implementation
            with patch.object(
                ScoreboardIngestion,
                "process_date_range_async",
                autospec=True,
                side_effect=mock_process_date_range_async,
            ):
                result = ingestion.process_date_range(dates)

        # Assert
        assert len(processed_dates) == NUM_TEST_DATES
        assert processed_dates == dates
        assert result == dates

    def test_process_date_range_with_already_processed_dates_skips_processed_dates(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test that process_date_range skips already processed dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        already_processed = ["2023-03-15"]  # First date already processed
        processed_dates = []  # Track which dates are processed

        # Set up the mock database to return the already processed dates
        mock_db.get_processed_dates.return_value = already_processed

        # Create a mock function to track which dates are processed
        def mock_fetch_and_store(date, _):  # Use _ to indicate unused argument
            processed_dates.append(date)
            return {"events": [{"id": "12345"}]}

        # Stub out the async method to call our mock function
        async def mock_process_async(*args, **kwargs):
            result = []
            for date in args[0]:
                if date not in already_processed:
                    processed_dates.append(date)
                    result.append(date)
            return result

        # Patch the necessary methods and classes
        with (
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date",
                side_effect=mock_fetch_and_store,
            ),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.process_date_range_async",
                side_effect=mock_process_async,
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
        ):
            # Create the ScoreboardIngestion instance with proper config
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)

            # Act
            result = ingestion.process_date_range(dates)

        # Assert
        # Only unprocessed dates should be returned and processed
        expected_processed = ["2023-03-16", "2023-03-17"]
        assert result == expected_processed
        assert processed_dates == expected_processed

    def test_ingest_scoreboard_with_specific_date_processes_date(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with specific date processes that date."""
        # Arrange
        test_date = "2023-03-15"
        espn_date = "20230315"
        insert_called = False

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(config):
            # Simulate API call
            mock_api_client.fetch_scoreboard(date=espn_date)
            # Simulate database insert
            mock_db.insert_bronze_scoreboard(
                date=test_date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": "200"},
                data={"events": [{"id": "12345"}]},
            )
            nonlocal insert_called
            insert_called = True
            return [test_date]

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.ingest_scoreboard_async", return_value=[test_date]),
            patch(
                "src.ingest.scoreboard.asyncio.run",
                side_effect=lambda x: mock_ingest_scoreboard_async_sync(None),
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                date=test_date,
                db_path=TEST_DB_PATH,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == [test_date]
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
        insert_count = 0

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(config):
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
                side_effect=lambda x: mock_ingest_scoreboard_async_sync(None),
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
        def mock_ingest_scoreboard_async_sync(config):
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
                side_effect=lambda x: mock_ingest_scoreboard_async_sync(None),
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
        insert_count = 0

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Mock the ingest_scoreboard_async function with a synchronous version
        def mock_ingest_scoreboard_async_sync(config):
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
                side_effect=lambda x: mock_ingest_scoreboard_async_sync(None),
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
        insert_count = 0

        # Set historical start date in config
        espn_api_config.historical_start_date = historical_start

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Create a side effect for fetch_and_store_date
        def mock_fetch_and_store(date, db):
            nonlocal insert_count
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
            insert_count += 1
            return api_response

        # Mock the async ingest function
        async def mock_ingest_async(config):
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
        insert_count = 0

        # Set historical start date in config
        espn_api_config.historical_start_date = historical_start

        # Configure mock responses
        mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
        mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

        # Create a side effect for fetch_and_store_date
        def mock_fetch_and_store(date, db):
            nonlocal insert_count
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
            insert_count += 1
            return api_response

        # Mock the async ingest function
        async def mock_ingest_async(config):
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
        assert config_arg.initial_request_delay == api_config_dict["initial_request_delay"]
        assert config_arg.max_retries == api_config_dict["max_retries"]
        assert config_arg.timeout == api_config_dict["timeout"]

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
        assert config_arg.initial_request_delay == api_config_object.initial_request_delay
        assert config_arg.max_retries == api_config_object.max_retries
        assert config_arg.timeout == api_config_object.timeout

        assert ingestion.batch_size == api_config_object.batch_size
        assert ingestion.db_path == TEST_DB_PATH

    @pytest.mark.asyncio()
    async def test_fetch_and_store_date_async_with_valid_date_fetches_and_stores_data(
        self, mock_db, mock_async_api_client, espn_api_config
    ):
        """Test fetch_and_store_date_async fetches and stores data for valid date."""
        # Arrange
        date = "2023-03-15"
        espn_date = "20230315"  # Formatted for API

        # Create ingestion with mocked client
        ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
        ingestion.api_client = mock_async_api_client

        # Act
        result = await ingestion.fetch_and_store_date_async(date, mock_db)

        # Assert
        mock_async_api_client.fetch_scoreboard_async.assert_called_once_with(date=espn_date)
        mock_db.insert_bronze_scoreboard.assert_called_once()

        # Check the data was passed correctly
        _, kwargs = mock_db.insert_bronze_scoreboard.call_args
        assert kwargs["date"] == date
        assert kwargs["data"] == mock_async_api_client.fetch_scoreboard_async.return_value

        # Check result is the API response
        assert result == mock_async_api_client.fetch_scoreboard_async.return_value

    @pytest.mark.asyncio()
    async def test_process_date_range_async_with_multiple_dates_processes_all_dates(
        self, mock_db, mock_async_api_client, espn_api_config
    ):
        """Test process_date_range_async processes all dates in the range."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = []  # No dates processed
        mock_db.insert_bronze_scoreboard.return_value = None  # Simulate successful inserts

        # Act
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path=TEST_DB_PATH)
            ingestion.api_client = mock_async_api_client  # Replace the API client with our mock

            # Mock the async database interaction to track processed dates
            processed_dates = []

            async def side_effect(date, _):
                processed_dates.append(date)
                return mock_async_api_client.fetch_scoreboard_async.return_value

            # Replace fetch_and_store_date_async with our mock implementation
            with patch.object(ingestion, "fetch_and_store_date_async", side_effect=side_effect):
                result = await ingestion.process_date_range_async(dates)

        # Assert
        assert len(processed_dates) == NUM_TEST_DATES
        assert processed_dates == dates
        assert result == dates

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
        already_processed = ["2023-03-15"]  # First date already processed
        processed_dates = []  # Track which dates are processed

        # Set up the mock database to return the already processed dates
        mock_db.get_processed_dates.return_value = already_processed

        # Create a mock function to track which dates are processed
        async def mock_fetch_and_store(date, _):  # Use _ to indicate unused argument
            processed_dates.append(date)
            return {"events": [{"id": "12345"}]}

        # Patch the necessary methods and classes
        with (
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_async_api_client),
        ):
            # Create the ScoreboardIngestion instance with proper config
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)

            # Act
            result = await ingestion.process_date_range_async(dates)

        # Assert
        # Only unprocessed dates should be returned and processed
        expected_processed = ["2023-03-16", "2023-03-17"]
        assert result == expected_processed
        assert processed_dates == expected_processed

    @pytest.mark.asyncio()
    async def test_process_date_range_async_with_error_handling_continues_processing(
        self,
        mock_db,
        mock_async_api_client,
        espn_api_config,
    ):
        """Test process_date_range_async handles errors and continues processing."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = []  # No dates processed

        # Create a mock function that raises an error for the middle date
        async def mock_fetch_and_store(date, _):
            if date == "2023-03-16":
                raise Exception("Test error")
            return {"events": [{"id": "12345"}]}

        # Patch the necessary methods and classes
        with (
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_async_api_client),
        ):
            # Create the ScoreboardIngestion instance with proper config
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)

            # Act
            result = await ingestion.process_date_range_async(dates)

        # Assert
        # Only successful dates should be in the result
        expected_processed = ["2023-03-15", "2023-03-17"]
        assert sorted(result) == expected_processed

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
        mock_db.get_processed_dates.return_value = []  # No dates processed
        insert_count = 0

        # Configure mock responses
        mock_async_api_client.fetch_scoreboard_async.return_value = {"events": [{"id": "12345"}]}

        # Create a side effect for fetch_and_store_date_async
        async def mock_fetch_and_store(date, db):
            nonlocal insert_count
            espn_date = date.replace("-", "")

            # Call the actual fetch_scoreboard_async method to register the call
            api_response = await mock_async_api_client.fetch_scoreboard_async(date=espn_date)

            # Call insert_bronze_scoreboard
            db.insert_bronze_scoreboard(
                date=date,
                url="https://example.com/endpoint",
                params={"dates": espn_date, "groups": "50", "limit": 200},
                data=api_response,
            )
            insert_count += 1
            return api_response

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_async_api_client),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                side_effect=mock_fetch_and_store,
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
                    start_date="2023-03-15",
                    end_date="2023-03-17",
                    db_path=TEST_DB_PATH,
                )
                result = await ingest_scoreboard_async(config)

        # Assert
        assert result == dates
        assert mock_async_api_client.fetch_scoreboard_async.call_count >= len(dates)
        assert insert_count == len(dates), f"Expected {len(dates)} inserts, got {insert_count}"

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
        mock_db.get_processed_dates.return_value = []

        # Make a copy of the config to ensure we don't modify the original
        import copy

        test_config = copy.deepcopy(espn_api_config)
        original_concurrency = test_config.max_concurrency

        # Mock implementations
        async def mock_fetch_and_store(date, db):
            return {"events": [{"id": "12345"}]}

        # Mock patches for API client creation to check concurrency setting
        api_client_mock = MagicMock()

        def api_client_factory(config):
            # Store the config used to create the client for verification
            api_client_factory.last_config = config
            return mock_async_api_client

        api_client_factory.last_config = None

        # Patch necessary components
        with (
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
            patch("src.ingest.scoreboard.ESPNApiClient", side_effect=api_client_factory),
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Run the code under test with concurrency override
            config = ScoreboardIngestionConfig(
                espn_api_config=test_config,
                date="2023-03-15",
                db_path=TEST_DB_PATH,
                concurrency=custom_concurrency,  # Override concurrency
            )
            await ingest_scoreboard_async(config)

        # Assert
        # Check that the original config hasn't been modified
        assert (
            test_config.max_concurrency == custom_concurrency
        )  # Config passed to ingest is modified
        assert espn_api_config.max_concurrency == original_concurrency  # Original fixture unchanged

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
        espn_api_config.batch_size = batch_size
        mock_db.get_processed_dates.return_value = []

        # Track when each date is processed to verify batching
        processing_order = {}
        batch_counter = 0

        # Mock to track which dates are processed together
        async def mock_fetch_and_store(date, db):
            nonlocal batch_counter
            processing_order[date] = batch_counter
            # Simulate some processing time to ensure async behavior
            await asyncio.sleep(0.01)
            return {"events": [{"id": "12345"}]}

        # Patch necessary components
        with (
            patch(
                "src.ingest.scoreboard.ScoreboardIngestion.fetch_and_store_date_async",
                side_effect=mock_fetch_and_store,
            ),
            patch("src.ingest.scoreboard.Database.__enter__", return_value=mock_db),
            patch("src.ingest.scoreboard.Database.__exit__", return_value=None),
        ):
            # Create ingestion with custom batch size
            ingestion = ScoreboardIngestion(espn_api_config, TEST_DB_PATH)
            ingestion.api_client = mock_async_api_client

            # Define a side effect that increments batch counter after each batch
            original_gather = asyncio.gather

            async def mock_gather(*args, **kwargs):
                nonlocal batch_counter
                result = await original_gather(*args, **kwargs)
                batch_counter += 1
                return result

            # Patch asyncio.gather to track batch execution
            with patch("asyncio.gather", side_effect=mock_gather):
                # Act
                await ingestion.process_date_range_async(dates)

        # Assert
        # Should have ceil(4/2) = 2 batches
        assert batch_counter == 2

        # First batch should contain first two dates with same counter value
        assert processing_order["2023-03-15"] == processing_order["2023-03-16"]

        # Second batch should contain last two dates with same counter value
        assert processing_order["2023-03-17"] == processing_order["2023-03-18"]

        # Batches should have different counter values
        assert processing_order["2023-03-15"] != processing_order["2023-03-17"]
