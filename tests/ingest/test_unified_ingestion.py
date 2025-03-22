"""Tests for the unified ingestion module.

This module tests the functions in ingest_all.py that orchestrate multiple
ingestion endpoints.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.ingest.ingest_all import (
    UnifiedIngestionConfig,
    get_valid_endpoints,
    ingest_multiple_endpoints,
)
from src.utils.config import ESPNApiConfig, RequestSettings


@pytest.fixture
def mock_espn_api_config():
    """Create a mock ESPN API configuration."""
    return ESPNApiConfig(
        base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        v3_base_url="https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball",
        endpoints={
            "scoreboard": "scoreboard?dates={date}",
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
def mock_scoreboard_config():
    """Create a mock scoreboard configuration."""
    return MagicMock()


@pytest.fixture
def mock_teams_config():
    """Create a mock teams configuration."""
    return MagicMock()


@pytest.fixture
def mock_config_factory():
    """Create mock configuration factory functions."""
    return {
        "scoreboard": MagicMock(return_value=MagicMock()),
        "teams": MagicMock(return_value=MagicMock()),
    }


@pytest.mark.asyncio
@patch("src.ingest.ingest_all.ingest_scoreboard_async")
async def test_ingest_multiple_endpoints_scoreboard(mock_ingest_scoreboard, mock_espn_api_config):
    """Test that ingest_multiple_endpoints calls the appropriate function for scoreboard."""
    # Arrange
    processed_dates = [date(2023, 1, 1)]
    mock_ingest_scoreboard.return_value = processed_dates

    config = UnifiedIngestionConfig(
        espn_api_config=mock_espn_api_config,
        endpoints=["scoreboard"],
        date="2023-01-01",
    )

    # Act
    result = await ingest_multiple_endpoints(config)

    # Assert
    assert result == {"scoreboard": processed_dates}
    mock_ingest_scoreboard.assert_called_once()


@pytest.mark.asyncio
@patch("src.ingest.ingest_all.ingest_teams_async")
async def test_ingest_multiple_endpoints_teams(mock_ingest_teams, mock_espn_api_config):
    """Test that ingest_multiple_endpoints calls the appropriate function for teams."""
    # Arrange
    processed_pages = [1]
    mock_ingest_teams.return_value = processed_pages

    config = UnifiedIngestionConfig(
        espn_api_config=mock_espn_api_config,
        endpoints=["teams"],
    )

    # Act
    result = await ingest_multiple_endpoints(config)

    # Assert
    assert result == {"teams": processed_pages}
    mock_ingest_teams.assert_called_once()


@pytest.mark.asyncio
@patch("src.ingest.ingest_all.ingest_scoreboard_async")
@patch("src.ingest.ingest_all.ingest_teams_async")
async def test_ingest_multiple_endpoints_all(
    mock_ingest_teams, mock_ingest_scoreboard, mock_espn_api_config
):
    """Test that ingest_multiple_endpoints calls all appropriate functions."""
    # Arrange
    processed_dates = [date(2023, 1, 1)]
    processed_pages = [1]
    mock_ingest_scoreboard.return_value = processed_dates
    mock_ingest_teams.return_value = processed_pages

    config = UnifiedIngestionConfig(
        espn_api_config=mock_espn_api_config,
        endpoints=["scoreboard", "teams"],
        date="2023-01-01",
    )

    # Act
    result = await ingest_multiple_endpoints(config)

    # Assert
    assert result == {
        "scoreboard": processed_dates,
        "teams": processed_pages,
    }
    mock_ingest_scoreboard.assert_called_once()
    mock_ingest_teams.assert_called_once()


def test_get_valid_endpoints():
    """Test that get_valid_endpoints returns the correct list of endpoints."""
    # Act
    result = get_valid_endpoints()

    # Assert
    assert isinstance(result, list | set)
    assert "scoreboard" in result
    assert "teams" in result
