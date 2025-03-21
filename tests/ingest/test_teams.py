"""Tests for ESPN Basketball Teams API data ingestion.

This module contains tests for the ESPN Basketball Teams API data ingestion,
including API connection, data fetching, and storage functionality.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.ingest.teams import TeamsIngestionConfig, ingest_teams
from src.utils.espn_api_client import ESPNApiConfig


@pytest.fixture
def mock_espn_api_config():
    """Create a mock ESPN API configuration for testing."""
    return ESPNApiConfig(
        base_url="https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball",
        endpoints={
            "teams": "/seasons/{season}/teams",
        },
        initial_request_delay=0.01,
        max_retries=1,
        timeout=1.0,
        max_concurrency=1,
    )


@pytest.fixture
def mock_teams_response_page1():
    """Mock response for teams API - page 1."""
    return {
        "count": 150,
        "pageIndex": 1,
        "pageSize": 100,
        "pageCount": 2,
        "items": [
            {
                "id": "1",
                "uid": "s:40~l:41~t:1",
                "guid": "1",
                "slug": "team-1",
                "location": "School 1",
                "name": "Team 1",
                "nickname": "Team1",
                "abbreviation": "TM1",
                "displayName": "School 1 Team 1",
                "shortDisplayName": "Team 1",
                "color": "123456",
                "alternateColor": "654321",
                "active": True,
                "isAllStar": False,
            },
            {
                "id": "2",
                "uid": "s:40~l:41~t:2",
                "guid": "2",
                "slug": "team-2",
                "location": "School 2",
                "name": "Team 2",
                "nickname": "Team2",
                "abbreviation": "TM2",
                "displayName": "School 2 Team 2",
                "shortDisplayName": "Team 2",
                "color": "234567",
                "alternateColor": "765432",
                "active": True,
                "isAllStar": False,
            },
        ],
    }


@pytest.fixture
def mock_teams_response_page2():
    """Mock response for teams API - page 2."""
    return {
        "count": 150,
        "pageIndex": 2,
        "pageSize": 100,
        "pageCount": 2,
        "items": [
            {
                "id": "3",
                "uid": "s:40~l:41~t:3",
                "guid": "3",
                "slug": "team-3",
                "location": "School 3",
                "name": "Team 3",
                "nickname": "Team3",
                "abbreviation": "TM3",
                "displayName": "School 3 Team 3",
                "shortDisplayName": "Team 3",
                "color": "345678",
                "alternateColor": "876543",
                "active": True,
                "isAllStar": False,
            },
        ],
    }


@pytest.fixture
def mock_empty_teams_response():
    """Mock empty response for teams API."""
    return {
        "count": 0,
        "pageIndex": 1,
        "pageSize": 100,
        "pageCount": 0,
        "items": [],
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory for test data."""
    output_dir = tmp_path / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_fetch_teams_success(mock_espn_api_config, mock_teams_response_page1):
    """Test successful API data retrieval for teams."""
    with patch("src.ingest.teams.ESPNApiClient") as mock_client_class:
        # Set up mock client
        mock_client = mock_client_class.return_value
        mock_client._request.return_value = mock_teams_response_page1
        mock_client.get_endpoint_url.return_value = "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2023/teams"
        
        # Create config
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            season="2023",
        )
        
        # Import here to avoid circular imports
        from src.ingest.teams import fetch_teams
        
        # Call the function
        result = fetch_teams(config)
        
        # Verify the expected URL was called
        mock_client.get_endpoint_url.assert_called_once_with("teams", season="2023")
        mock_client._request.assert_called_once()
        
        # Verify results
        assert len(result["items"]) == 2
        assert result["count"] == 150
        assert result["pageCount"] == 2


def test_fetch_teams_pagination(mock_espn_api_config, mock_teams_response_page1, mock_teams_response_page2):
    """Test correct handling of paginated responses."""
    with patch("src.ingest.teams.ESPNApiClient") as mock_client_class:
        # Set up mock client
        mock_client = mock_client_class.return_value
        mock_client._request.side_effect = [mock_teams_response_page1, mock_teams_response_page2]
        
        # Create config
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            season="2023",
            limit=100,  # Set to trigger pagination
        )
        
        # Import here to avoid circular imports
        from src.ingest.teams import fetch_teams_all_pages
        
        # Call the function
        result = fetch_teams_all_pages(config)
        
        # Verify multiple calls were made
        assert mock_client._request.call_count == 2
        
        # Verify results
        assert len(result["items"]) == 3  # Combined items from both pages
        assert result["count"] == 150
        
        # Verify both teams from page 1 and the team from page 2 are in the results
        team_ids = [team["id"] for team in result["items"]]
        assert "1" in team_ids
        assert "2" in team_ids
        assert "3" in team_ids


def test_fetch_teams_historical(mock_espn_api_config, mock_teams_response_page1):
    """Test fetching teams from past seasons."""
    with patch("src.ingest.teams.ESPNApiClient") as mock_client_class:
        # Set up mock client
        mock_client = mock_client_class.return_value
        mock_client._request.return_value = mock_teams_response_page1
        mock_client.get_endpoint_url.return_value = "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2010/teams"
        
        # Create config for a past season
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            season="2010",
        )
        
        # Import here to avoid circular imports
        from src.ingest.teams import fetch_teams
        
        # Call the function
        result = fetch_teams(config)
        
        # Verify the expected URL was called with the historical season
        mock_client.get_endpoint_url.assert_called_once_with("teams", season="2010")
        mock_client._request.assert_called_once()
        
        # Verify results
        assert len(result["items"]) == 2
        assert result["count"] == 150


def test_store_teams_parquet(mock_espn_api_config, mock_teams_response_page1, temp_output_dir):
    """Test storing teams data in Parquet format."""
    with patch("src.ingest.teams.ParquetStorage") as MockParquetStorage:
        # Set up mock storage
        mock_storage = MockParquetStorage.return_value
        mock_storage.write_team_data.return_value = {"success": True, "file_path": "test/path.parquet"}
        
        # Create config
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            season="2023",
            parquet_dir=str(temp_output_dir),
        )
        
        # Import here to avoid circular imports
        from src.ingest.teams import store_teams_data
        
        # Call the function
        result = store_teams_data(config, mock_teams_response_page1)
        
        # Verify storage was called with the correct parameters
        mock_storage.write_team_data.assert_called_once()
        call_kwargs = mock_storage.write_team_data.call_args[1]
        
        # Check parameters
        assert "source_url" in call_kwargs
        assert "parameters" in call_kwargs
        assert call_kwargs["parameters"]["season"] == "2023"
        assert call_kwargs["data"] == mock_teams_response_page1
        
        # Check result
        assert result["success"] is True


def test_fetch_teams_error_handling(mock_espn_api_config):
    """Test handling of API errors or timeouts."""
    with patch("src.ingest.teams.ESPNApiClient") as mock_client_class:
        # Set up mock client to raise an exception
        mock_client = mock_client_class.return_value
        mock_client._request.side_effect = Exception("API timeout")
        
        # Create config
        config = TeamsIngestionConfig(
            espn_api_config=mock_espn_api_config,
            season="2023",
        )
        
        # Import here to avoid circular imports
        from src.ingest.teams import fetch_teams
        
        # Call the function and expect an exception
        with pytest.raises(Exception) as excinfo:
            fetch_teams(config)
        
        # Verify error handling
        assert "API timeout" in str(excinfo.value)


def test_ingest_teams_integration(mock_espn_api_config, mock_teams_response_page1, temp_output_dir):
    """Test the complete integration of fetching and storing team data."""
    with patch("src.ingest.teams.ESPNApiClient") as mock_client_class:
        # Set up mock client
        mock_client = mock_client_class.return_value
        mock_client._request.return_value = mock_teams_response_page1
        mock_client.get_endpoint_url.return_value = "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2023/teams"
        
        # Mock the fetch_teams_all_pages function to avoid pagination
        with patch("src.ingest.teams.fetch_teams_all_pages") as mock_fetch_all:
            mock_fetch_all.return_value = mock_teams_response_page1
            
            with patch("src.ingest.teams.ParquetStorage") as MockParquetStorage:
                # Set up mock storage
                mock_storage = MockParquetStorage.return_value
                mock_storage.write_team_data.return_value = {"success": True, "file_path": "test/path.parquet"}
                
                # Call ingest_teams with a specific season
                result = ingest_teams("", ["2023"], mock_espn_api_config, str(temp_output_dir))
                
                # Verify fetch_teams_all_pages was called (not _request directly)
                mock_fetch_all.assert_called_once()
                
                # Verify storage was called with the correct parameters
                mock_storage.write_team_data.assert_called_once()
                
                # Check result type
                assert isinstance(result, list)
                assert len(result) == 1  # One season processed 