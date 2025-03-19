import pytest
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, call

from src.ingest.scoreboard import ScoreboardIngestion, ingest_scoreboard
from src.utils.config import ESPNApiConfig
from src.utils.database import Database

class TestScoreboardIngestionModule:
    """Tests for the scoreboard ingestion module."""
    
    @pytest.fixture
    def espn_api_config(self):
        """Create a test ESPNApiConfig instance."""
        return ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={
                "scoreboard": "/scoreboard",
                "teams": "/teams",
                "team_detail": "/teams/{team_id}",
                "game_summary": "/summary"
            },
            request_delay=0.01,  # Fast for testing
            max_retries=1,
            timeout=1.0,
            batch_size=10,
            historical_start_date="2023-01-01"
        )
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance."""
        mock = MagicMock(spec=Database)
        mock.get_processed_dates.return_value = []
        return mock
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock ESPNApiClient instance."""
        with patch("src.ingest.scoreboard.ESPNApiClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.fetch_scoreboard = MagicMock()
            mock_client._build_url.return_value = "https://example.com/scoreboard"
            
            # Sample API response
            sample_data = {
                "events": [
                    {
                        "id": "401470291",
                        "date": "2023-02-28T00:00Z",
                        "name": "Duke vs North Carolina",
                        "competitions": [
                            {
                                "id": "401470291",
                                "competitors": [
                                    {
                                        "id": "150",
                                        "team": {"id": "150", "name": "Duke"},
                                        "homeAway": "home",
                                        "score": "75"
                                    },
                                    {
                                        "id": "153",
                                        "team": {"id": "153", "name": "North Carolina"},
                                        "homeAway": "away",
                                        "score": "70"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            mock_client.fetch_scoreboard.return_value = sample_data
            mock_client_cls.return_value = mock_client
            yield mock_client
    
    def test_fetch_and_store_date_WithValidDate_FetchesAndStoresData(self, espn_api_config, mock_db, mock_api_client):
        """Test fetching and storing data for a specific date."""
        # Arrange
        ingestion = ScoreboardIngestion(espn_api_config)
        ingestion.api_client = mock_api_client
        
        date = "2023-02-28"
        
        # Act
        ingestion.fetch_and_store_date(date, mock_db)
        
        # Assert
        # Check that the API was called properly
        mock_api_client.fetch_scoreboard.assert_called_once_with("20230228")
        
        # Check that the database was updated
        mock_db.insert_bronze_scoreboard.assert_called_once()
        args = mock_db.insert_bronze_scoreboard.call_args[0]
        
        assert args[0] == date  # Date
        assert args[1] == "https://example.com/scoreboard"  # URL
        assert args[2]["dates"] == "20230228"  # Params
        assert "events" in args[3]  # Data
    
    def test_process_date_range_WithMultipleDates_ProcessesAllDates(self, espn_api_config, mock_db, mock_api_client):
        """Test processing a range of dates."""
        # Arrange
        with patch("src.ingest.scoreboard.Database") as mock_db_cls:
            mock_db_cls.return_value.__enter__.return_value = mock_db
            
            ingestion = ScoreboardIngestion(espn_api_config)
            ingestion.api_client = mock_api_client
            
            dates = ["2023-02-28", "2023-03-01", "2023-03-02"]
            
            # Act
            ingestion.process_date_range(dates)
            
            # Assert
            # Check that the database was queried for processed dates
            mock_db.get_processed_dates.assert_called_once()
            
            # Each date should have been processed
            assert mock_api_client.fetch_scoreboard.call_count == 3
            
            # Check database inserts
            assert mock_db.insert_bronze_scoreboard.call_count == 3
    
    def test_process_date_range_WithAlreadyProcessedDates_SkipsProcessedDates(self, espn_api_config, mock_db, mock_api_client):
        """Test that already processed dates are skipped."""
        # Arrange
        with patch("src.ingest.scoreboard.Database") as mock_db_cls:
            mock_db_cls.return_value.__enter__.return_value = mock_db
            
            # Set some dates as already processed
            mock_db.get_processed_dates.return_value = ["2023-02-28", "2023-03-01"]
            
            ingestion = ScoreboardIngestion(espn_api_config)
            ingestion.api_client = mock_api_client
            
            dates = ["2023-02-28", "2023-03-01", "2023-03-02"]
            
            # Act
            ingestion.process_date_range(dates)
            
            # Assert
            # Should only process the one unprocessed date
            assert mock_api_client.fetch_scoreboard.call_count == 1
            mock_api_client.fetch_scoreboard.assert_called_once_with("20230302")
            
            # Check database inserts
            assert mock_db.insert_bronze_scoreboard.call_count == 1
    
    def test_ingest_scoreboard_WithSpecificDate_ProcessesDate(self, espn_api_config):
        """Test ingesting data for a specific date."""
        # Arrange
        with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls:
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            
            # Act
            ingest_scoreboard(date="2023-02-28", espn_api_config=espn_api_config)
            
            # Assert
            # Check that the ingestion class was created correctly
            mock_ingestion_cls.assert_called_once_with(espn_api_config, "data/ncaa.duckdb")
            
            # Check that process_date_range was called with the expected dates
            mock_ingestion.process_date_range.assert_called_once_with(["2023-02-28"])
    
    def test_ingest_scoreboard_WithDateRange_ProcessesDateRange(self, espn_api_config):
        """Test ingesting data for a date range."""
        # Arrange
        with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
             patch("src.ingest.scoreboard.generate_date_range") as mock_generate_range:
            
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            
            # Mock date range generation
            mock_generate_range.return_value = ["2023-02-28", "2023-03-01", "2023-03-02"]
            
            # Act
            ingest_scoreboard(
                start_date="2023-02-28", 
                end_date="2023-03-02",
                espn_api_config=espn_api_config
            )
            
            # Assert
            # Check date range generation
            mock_generate_range.assert_called_once_with("2023-02-28", "2023-03-02")
            
            # Check that the process was called with generated dates
            mock_ingestion.process_date_range.assert_called_once_with(["2023-02-28", "2023-03-01", "2023-03-02"])
    
    def test_ingest_scoreboard_WithYesterdayFlag_ProcessesYesterday(self, espn_api_config):
        """Test ingesting data with yesterday flag."""
        # Arrange
        with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
             patch("src.ingest.scoreboard.get_yesterday") as mock_get_yesterday:
            
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            
            # Mock yesterday date
            mock_get_yesterday.return_value = "2023-03-14"
            
            # Act
            ingest_scoreboard(
                yesterday=True,
                espn_api_config=espn_api_config
            )
            
            # Assert
            # Check yesterday date retrieval
            mock_get_yesterday.assert_called_once()
            
            # Check that the process was called with yesterday's date
            mock_ingestion.process_date_range.assert_called_once_with(["2023-03-14"])
    
    def test_ingest_scoreboard_WithSeason_ProcessesSeasonDates(self, espn_api_config):
        """Test ingesting data for a specific season."""
        # Arrange
        with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
             patch("src.ingest.scoreboard.get_season_date_range") as mock_get_season, \
             patch("src.ingest.scoreboard.generate_date_range") as mock_generate_range:
            
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            
            # Mock season date range function
            mock_get_season.return_value = ("2022-11-01", "2023-04-30")
            
            # Mock date range generation
            mock_generate_range.return_value = ["2022-11-01", "2022-11-02", "2022-11-03"]
            
            # Act
            ingest_scoreboard(
                seasons=["2022-23"],
                espn_api_config=espn_api_config
            )
            
            # Assert
            # Check that season range was requested
            mock_get_season.assert_called_once_with("2022-23")
            
            # Check that date range was generated
            mock_generate_range.assert_called_once_with("2022-11-01", "2023-04-30")
            
            # Check that the process was called with season dates
            mock_ingestion.process_date_range.assert_called_once_with(["2022-11-01", "2022-11-02", "2022-11-03"])
    
    def test_ingest_scoreboard_WithNoParameters_UsesHistoricalStartDate(self, espn_api_config):
        """Test ingesting data with no parameters uses historical start date."""
        # Arrange
        with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
             patch("src.ingest.scoreboard.get_yesterday") as mock_get_yesterday, \
             patch("src.ingest.scoreboard.generate_date_range") as mock_generate_range:
            
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            
            # Mock yesterday date
            mock_get_yesterday.return_value = "2023-03-14"
            
            # Mock date range generation
            mock_generate_range.return_value = ["2023-01-01", "2023-01-02", "2023-01-03"]
            
            # Act
            ingest_scoreboard(
                espn_api_config=espn_api_config
            )
            
            # Assert
            # Check that date range was generated from historical start date to yesterday
            mock_generate_range.assert_called_once_with("2023-01-01", "2023-03-14")
            
            # Check that the process was called with historical dates
            mock_ingestion.process_date_range.assert_called_once_with(["2023-01-01", "2023-01-02", "2023-01-03"]) 