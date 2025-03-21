"""ESPN Basketball Teams API data ingestion module.

This module contains functionality for fetching and storing NCAA basketball team data
from the ESPN API, including team metadata, colors, and status information.
It supports fetching both current and historical team data across multiple seasons.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from src.utils.config import ESPNApiConfig
from src.utils.espn_api_client import ESPNApiClient
from src.utils.parquet_storage import ParquetStorage

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class TeamsIngestionConfig:
    """Configuration for teams data ingestion."""

    # API configuration
    espn_api_config: ESPNApiConfig

    # Data storage configuration
    parquet_dir: str = "data/raw"

    # Season to fetch
    season: str = ""

    # Conference ID filter (optional)
    conference: str = ""

    # Pagination parameters
    limit: int = 100
    page: int = 1

    # Processing options
    force_update: bool = False


def fetch_teams(config: TeamsIngestionConfig) -> Dict[str, Any]:
    """Fetch team data for a specific season.

    Args:
        config: Teams ingestion configuration

    Returns:
        Dictionary containing team data

    Raises:
        Exception: If API request fails
    """
    # Create API client
    client = ESPNApiClient(config.espn_api_config)

    # Build URL parameters
    params = {
        "limit": config.limit,
        "page": config.page,
    }

    # Add conference filter if specified
    if config.conference:
        params["groups"] = config.conference

    # Build URL
    url = client.get_endpoint_url("teams", season=config.season)
    logger.info(
        "Fetching teams data",
        url=url,
        season=config.season,
        conference=config.conference if config.conference else "all",
        limit=config.limit,
        page=config.page,
    )

    # Make request
    try:
        response = client._request(url, params)
        logger.info(
            "Fetched teams data successfully",
            season=config.season,
            count=response.get("count", 0),
            page=response.get("pageIndex", 1),
            page_count=response.get("pageCount", 1),
        )
        return response
    except Exception as e:
        logger.error(
            "Failed to fetch teams data",
            season=config.season,
            error=str(e),
        )
        raise


def fetch_teams_all_pages(config: TeamsIngestionConfig) -> Dict[str, Any]:
    """Fetch all pages of team data for a specific season.

    Args:
        config: Teams ingestion configuration

    Returns:
        Dictionary containing combined team data from all pages

    Raises:
        Exception: If API request fails
    """
    # Fetch first page
    first_page = fetch_teams(config)

    # Extract pagination info
    total_pages = first_page.get("pageCount", 1)
    current_page = first_page.get("pageIndex", 1)

    # If only one page, return immediately
    if total_pages <= 1:
        return first_page

    # Initialize with first page data
    all_teams = {
        "count": first_page.get("count", 0),
        "pageIndex": 1,
        "pageSize": first_page.get("pageSize", config.limit),
        "pageCount": total_pages,
        "items": first_page.get("items", []),
    }

    # Fetch remaining pages
    for page in range(current_page + 1, total_pages + 1):
        # Update page in config
        page_config = TeamsIngestionConfig(
            espn_api_config=config.espn_api_config,
            parquet_dir=config.parquet_dir,
            season=config.season,
            conference=config.conference,
            limit=config.limit,
            page=page,
            force_update=config.force_update,
        )

        # Fetch page
        page_data = fetch_teams(page_config)

        # Add items to combined result
        all_teams["items"].extend(page_data.get("items", []))

    logger.info(
        "Fetched all team pages",
        season=config.season,
        total_pages=total_pages,
        total_teams=len(all_teams["items"]),
    )

    return all_teams


def store_teams_data(config: TeamsIngestionConfig, data: Dict[str, Any]) -> Dict[str, Any]:
    """Store team data in Parquet format.

    Args:
        config: Teams ingestion configuration
        data: Team data from API

    Returns:
        Dictionary with success status and file information
    """
    # Create storage handler
    storage = ParquetStorage(config.parquet_dir)

    # Build API URL for metadata
    client = ESPNApiClient(config.espn_api_config)
    source_url = client.get_endpoint_url("teams", season=config.season)

    # Create parameters object
    parameters = {
        "season": config.season,
        "limit": config.limit,
        "page": config.page,
    }
    if config.conference:
        parameters["conference"] = config.conference

    # Store data
    result = storage.write_team_data(
        source_url=source_url,
        parameters=parameters,
        data=data,
    )

    if result["success"]:
        logger.info(
            "Stored team data successfully",
            season=config.season,
            file_path=result.get("file_path", ""),
            team_count=len(data.get("items", [])),
        )
    else:
        logger.error(
            "Failed to store team data",
            season=config.season,
            error=result.get("error", "Unknown error"),
        )

    return result


def ingest_teams(
    conference: Optional[str] = None,
    seasons: Optional[List[str]] = None,
    espn_api_config: Optional[ESPNApiConfig] = None,
    parquet_dir: str = "data/raw",
) -> List[str]:
    """Ingest team data for specified seasons.

    Args:
        conference: Conference ID to filter (optional)
        seasons: List of seasons to fetch (YYYY format)
        espn_api_config: ESPN API configuration
        parquet_dir: Directory for output Parquet files

    Returns:
        List of processed seasons
    """
    # Use default config if not provided
    if espn_api_config is None:
        from src.utils.config import get_config
        from pathlib import Path

        config = get_config(Path("config"))
        espn_api_config = config.espn_api

    # Use current season if no seasons specified
    if not seasons:
        from src.utils.config import get_config
        from pathlib import Path

        config = get_config(Path("config"))
        current_season = config.seasons.current.split("-")[0]  # Extract first year from "YYYY-YY"
        seasons = [current_season]

    # Initialize processed seasons list
    processed_seasons = []

    # Process each season
    for season in seasons:
        logger.info(f"Processing season {season}")

        # Create config for this season
        config = TeamsIngestionConfig(
            espn_api_config=espn_api_config,
            parquet_dir=parquet_dir,
            season=season,
            conference=conference or "",
        )

        try:
            # Fetch all pages of team data
            team_data = fetch_teams_all_pages(config)

            # Store data
            result = store_teams_data(config, team_data)

            if result["success"]:
                processed_seasons.append(season)
                logger.info(f"Successfully processed season {season}")
            else:
                logger.error(f"Failed to store data for season {season}")

        except Exception as e:
            logger.error(f"Error processing season {season}: {str(e)}")
            continue

    # Return list of successfully processed seasons
    return processed_seasons 