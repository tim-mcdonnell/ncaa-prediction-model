import pytest
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingest.scoreboard import ScoreboardIngestion, ingest_scoreboard
from src.utils.config import ESPNApiConfig
from src.utils.database import Database

# Fixture for ESPN API configuration
@pytest.fixture
def espn_api_config():
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

# Fixture for mock database
@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    mock = MagicMock(spec=Database)
    mock.get_processed_dates.return_value = []
    return mock

# Fixture for mock API client
@pytest.fixture
def mock_api_client():
    """Create a mock ESPNApiClient instance."""
    with patch("src.ingest.scoreboard.ESPNApiClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.fetch_scoreboard = AsyncMock()
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

# Test fetch_and_store_date method
@pytest.mark.asyncio
async def test_fetch_and_store_date(espn_api_config, mock_db, mock_api_client):
    """Test fetching and storing data for a specific date."""
    ingestion = ScoreboardIngestion(espn_api_config)
    ingestion.api_client = mock_api_client
    
    date = "2023-02-28"
    await ingestion.fetch_and_store_date(date, mock_db)
    
    # Check that the API was called properly
    mock_api_client.fetch_scoreboard.assert_called_once_with("20230228")
    
    # Check that the database was updated
    mock_db.insert_bronze_scoreboard.assert_called_once()
    args = mock_db.insert_bronze_scoreboard.call_args[0]
    
    assert args[0] == date  # Date
    assert args[1] == "https://example.com/scoreboard"  # URL
    assert args[2]["dates"] == "20230228"  # Params
    assert "events" in args[3]  # Data

# Test process_date_range method
@pytest.mark.asyncio
async def test_process_date_range(espn_api_config, mock_db, mock_api_client):
    """Test processing a range of dates."""
    with patch("src.ingest.scoreboard.Database") as mock_db_cls:
        mock_db_cls.return_value.__enter__.return_value = mock_db
        
        ingestion = ScoreboardIngestion(espn_api_config)
        ingestion.api_client = mock_api_client
        
        dates = ["2023-02-28", "2023-03-01", "2023-03-02"]
        await ingestion.process_date_range(dates)
        
        # Check that the database was queried for processed dates
        mock_db.get_processed_dates.assert_called_once()
        
        # Each date should have been processed
        assert mock_api_client.fetch_scoreboard.call_count == 3
        
        # Check database inserts
        assert mock_db.insert_bronze_scoreboard.call_count == 3

# Test ingest_scoreboard function with specific date
def test_ingest_scoreboard_with_date(espn_api_config):
    """Test ingesting data for a specific date."""
    with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
         patch("src.ingest.scoreboard.asyncio.run") as mock_run:
        
        mock_ingestion = MagicMock()
        mock_ingestion.process_date_range = AsyncMock()
        mock_ingestion_cls.return_value = mock_ingestion
        
        ingest_scoreboard(date="2023-02-28", espn_api_config=espn_api_config)
        
        # Check that the process was called with the correct date
        mock_run.assert_called_once()
        
        # Extract arguments passed to process_date_range
        process_call = mock_run.call_args[0][0]
        
        # Ensure process_date_range would be called with the right arguments
        assert mock_ingestion.process_date_range == process_call._coro._obj

# Test ingest_scoreboard function with date range
def test_ingest_scoreboard_with_date_range(espn_api_config):
    """Test ingesting data for a date range."""
    with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
         patch("src.ingest.scoreboard.asyncio.run") as mock_run:
        
        mock_ingestion = MagicMock()
        mock_ingestion.process_date_range = AsyncMock()
        mock_ingestion_cls.return_value = mock_ingestion
        
        ingest_scoreboard(
            start_date="2023-02-28", 
            end_date="2023-03-02",
            espn_api_config=espn_api_config
        )
        
        # Check that the process was called
        mock_run.assert_called_once()
        
        # Extract arguments passed to process_date_range
        process_call = mock_run.call_args[0][0]
        
        # Ensure process_date_range would be called with the right arguments
        assert mock_ingestion.process_date_range == process_call._coro._obj

# Test ingest_scoreboard with season
def test_ingest_scoreboard_with_season(espn_api_config):
    """Test ingesting data for a specific season."""
    with patch("src.ingest.scoreboard.ScoreboardIngestion") as mock_ingestion_cls, \
         patch("src.ingest.scoreboard.asyncio.run") as mock_run, \
         patch("src.ingest.scoreboard.get_season_date_range") as mock_get_season:
        
        mock_ingestion = MagicMock()
        mock_ingestion.process_date_range = AsyncMock()
        mock_ingestion_cls.return_value = mock_ingestion
        
        # Mock season date range function
        mock_get_season.return_value = ("2022-11-01", "2023-04-30")
        
        ingest_scoreboard(
            seasons=["2022-23"],
            espn_api_config=espn_api_config
        )
        
        # Check that season range was requested
        mock_get_season.assert_called_once_with("2022-23")
        
        # Check that the process was called
        mock_run.assert_called_once()
        
        # Extract arguments passed to process_date_range
        process_call = mock_run.call_args[0][0]
        
        # Ensure process_date_range would be called with the right arguments
        assert mock_ingestion.process_date_range == process_call._coro._obj 