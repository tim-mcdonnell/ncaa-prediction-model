from unittest.mock import MagicMock, patch

import pytest

from src.ingest.scoreboard import ScoreboardIngestion, ScoreboardIngestionConfig, ingest_scoreboard
from src.utils.config import ESPNApiConfig
from src.utils.espn_api_client import ESPNApiClient

# Constants for test values
NUM_TEST_DATES = 3
NUM_UNPROCESSED_DATES = 2


class TestScoreboardIngestion:
    """Tests for the scoreboard data ingestion module."""

    @pytest.fixture()
    def espn_api_config(self):
        """Return a mock ESPN API configuration."""
        return {
            "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            "endpoints": {"scoreboard": "scoreboard"},
            "request_delay": 0.1,
            "max_retries": 3,
            "timeout": 10,
            "historical_start_date": "2022-11-01",
            "batch_size": 5,
        }

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
                            "competitors": [
                                {"id": "TeamA", "score": "75", "homeAway": "home"},
                                {"id": "TeamB", "score": "70", "homeAway": "away"},
                            ],
                        }
                    ],
                }
            ]
        }
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
            "base_url": "https://api.example.com",
            "endpoints": {"scoreboard": "sports/basketball/scoreboard"},
            "request_delay": 0.5,
            "max_retries": 2,
            "timeout": 5,
            "batch_size": 5,
        }

    @pytest.fixture()
    def api_config_object(self):
        """Object-style API configuration."""
        config = ESPNApiConfig(
            base_url="https://api.example.com",
            endpoints={"scoreboard": "sports/basketball/scoreboard"},
            request_delay=0.5,
            max_retries=2,
            timeout=5,
            batch_size=5,
        )
        return config

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
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path="test.db")
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

        # Act
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path="test.db")
            ingestion.api_client = mock_api_client  # Replace the API client with our mock

            # Mock the database interaction to track processed dates
            processed_dates = []

            def side_effect(date, _):
                processed_dates.append(date)
                return mock_api_client.fetch_scoreboard.return_value

            # Replace fetch_and_store_date with our mock implementation
            with patch.object(ingestion, "fetch_and_store_date", side_effect=side_effect):
                result = ingestion.process_date_range(dates)

        # Assert
        assert len(processed_dates) == NUM_TEST_DATES
        assert processed_dates == dates
        assert result == dates

    def test_process_date_range_with_already_processed_dates_skips_processed_dates(
        self, mock_db, mock_api_client, espn_api_config
    ):
        """Test process_date_range skips dates that have already been processed."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = ["2023-03-15"]  # One date already processed

        # Act
        with patch("src.ingest.scoreboard.Database", return_value=mock_db):
            ingestion = ScoreboardIngestion(espn_api_config=espn_api_config, db_path="test.db")
            ingestion.api_client = mock_api_client  # Replace the API client with our mock

            # Mock the database interaction to correctly handle already processed dates
            processed_dates = []

            def side_effect(date, _):
                processed_dates.append(date)
                return mock_api_client.fetch_scoreboard.return_value

            # Replace fetch_and_store_date with our mock implementation
            with patch.object(ingestion, "fetch_and_store_date", side_effect=side_effect):
                result = ingestion.process_date_range(dates)

        # Assert
        expected_processed = ["2023-03-16", "2023-03-17"]  # Only the unprocessed dates
        assert processed_dates == expected_processed
        assert result == expected_processed

    def test_ingest_scoreboard_with_specific_date_processes_date(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with specific date processes date."""
        # Arrange & Act
        mock_db.insert_bronze_scoreboard.return_value = None  # Simulate successful insert

        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
        ):
            # Format expected by ESPN API
            espn_date = "20230315"

            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                date="2023-03-15",
            )

            # Set up the expected API response pattern
            mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
            mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

            result = ingest_scoreboard(config)

        # Assert
        assert result == ["2023-03-15"]
        mock_api_client.fetch_scoreboard.assert_called_once_with(date=espn_date)

        # Check that insert_bronze_scoreboard was called with expected parameters
        mock_db.insert_bronze_scoreboard.assert_called_once()

    def test_ingest_scoreboard_with_date_range_processes_date_range(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with date range processes dates."""
        # Arrange
        dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        mock_db.get_processed_dates.return_value = []
        mock_db.insert_bronze_scoreboard.return_value = None

        # Act
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.get_date_range", return_value=dates),
        ):
            # Mock API client responses
            mock_api_client.fetch_scoreboard.return_value = {"events": [{"id": "12345"}]}
            mock_api_client.get_endpoint_url.return_value = "https://example.com/endpoint"

            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                start_date="2023-03-15",
                end_date="2023-03-17",
            )
            result = ingest_scoreboard(config)

        # Assert
        assert len(result) == NUM_TEST_DATES
        assert result == dates
        assert mock_api_client.fetch_scoreboard.call_count == NUM_TEST_DATES
        assert mock_db.insert_bronze_scoreboard.call_count == NUM_TEST_DATES

    def test_ingest_scoreboard_with_yesterday_flag_processes_yesterday(
        self,
        mock_db,
        mock_api_client,
        espn_api_config,
    ):
        """Test ingest_scoreboard with yesterday flag processes yesterday's date."""
        # Arrange & Act
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.get_yesterday", return_value="2023-03-14"),
        ):
            # Format expected by ESPN API
            espn_date = "20230314"
            config = ScoreboardIngestionConfig(
                espn_api_config=espn_api_config,
                yesterday=True,
            )
            result = ingest_scoreboard(config)

        # Assert
        assert result == ["2023-03-14"]
        mock_api_client.fetch_scoreboard.assert_called_once_with(date=espn_date)
        mock_db.insert_bronze_scoreboard.assert_called_once()

    def test_ingest_scoreboard_with_season_processes_entire_season(
        self,
        mock_api_client,
        mock_db,
        api_config_dict,
    ):
        """Test that ingest_scoreboard properly processes an entire season."""
        # Arrange
        season_dates = ["2023-03-01", "2023-03-02", "2023-03-03"]

        # Act
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch(
                "src.ingest.scoreboard.get_season_date_range",
                return_value=("2023-03-01", "2023-03-03"),
            ),
            patch(
                "src.ingest.scoreboard.get_date_range",
                return_value=season_dates,
            ),
        ):
            config = ScoreboardIngestionConfig(
                espn_api_config=api_config_dict,
                seasons=["2022-23"],
            )
            processed_dates = ingest_scoreboard(config)

        # Assert
        assert processed_dates == season_dates
        assert mock_api_client.fetch_scoreboard.call_count == NUM_TEST_DATES
        assert mock_db.insert_bronze_scoreboard.call_count == NUM_TEST_DATES

    def test_ingest_scoreboard_with_historical_processes_date_range(
        self,
        mock_api_client,
        api_config_dict,
    ):
        """Test that ingest_scoreboard properly processes a historical date range."""
        # Arrange
        historical_dates = ["2022-11-01", "2022-11-02", "2022-11-03"]

        # Act
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch(
                "src.ingest.scoreboard.get_date_range",
                return_value=historical_dates,
            ),
        ):
            config = ScoreboardIngestionConfig(
                espn_api_config=api_config_dict,
                start_date="2022-11-01",
                end_date="2022-11-03",
            )
            processed_dates = ingest_scoreboard(config)
            assert processed_dates == historical_dates

    def test_ingest_scoreboard_with_no_parameters_uses_historical_start_date(
        self,
        mock_db,
        mock_api_client,
        api_config_object,
    ):
        """Test ingest_scoreboard with no parameters uses historical start date."""
        # Arrange
        historical_dates = ["2022-11-01", "2022-11-02", "2022-11-03"]

        # Update the api_config_object with historical_start_date
        api_config_object.historical_start_date = "2022-11-01"

        # Act
        with (
            patch("src.ingest.scoreboard.ESPNApiClient", return_value=mock_api_client),
            patch("src.ingest.scoreboard.Database", return_value=mock_db),
            patch("src.ingest.scoreboard.get_date_range", return_value=historical_dates),
            patch("src.ingest.scoreboard.get_yesterday", return_value="2022-11-03"),
        ):
            config = ScoreboardIngestionConfig(espn_api_config=api_config_object)
            result = ingest_scoreboard(config)

        # Assert
        assert result == historical_dates
        assert mock_api_client.fetch_scoreboard.call_count == NUM_TEST_DATES
        assert mock_db.insert_bronze_scoreboard.call_count == NUM_TEST_DATES

    def test_init_with_dict_config(self, mock_api_client_with_patch, api_config_dict):
        """Test initialization with dictionary configuration."""
        ingestion = ScoreboardIngestion(api_config_dict, db_path="test.db")

        mock_api_client_with_patch.assert_called_once_with(
            base_url=api_config_dict["base_url"],
            endpoints=api_config_dict["endpoints"],
            request_delay=api_config_dict["request_delay"],
            max_retries=api_config_dict["max_retries"],
            timeout=api_config_dict["timeout"],
        )

        assert ingestion.batch_size == api_config_dict["batch_size"]
        assert ingestion.db_path == "test.db"

    def test_init_with_object_config(self, mock_api_client_with_patch, api_config_object):
        """Test initialization with object configuration."""
        ingestion = ScoreboardIngestion(api_config_object, db_path="test.db")

        mock_api_client_with_patch.assert_called_once_with(
            base_url=api_config_object.base_url,
            endpoints=api_config_object.endpoints,
            request_delay=api_config_object.request_delay,
            max_retries=api_config_object.max_retries,
            timeout=api_config_object.timeout,
        )

        assert ingestion.batch_size == api_config_object.batch_size
        assert ingestion.db_path == "test.db"
