"""ESPN Basketball Teams API data ingestion module.

This module contains functionality for fetching and storing NCAA basketball team data
from the ESPN API, including team metadata, colors, and status information.
It supports fetching both current and historical team data across multiple seasons.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from src.utils.config import ESPNApiConfig, get_config
from src.utils.espn_api_client import ESPNApiClient
from src.utils.espn_api_client import ESPNApiConfig as ClientAPIConfig
from src.utils.parquet_storage import ParquetStorage

# Initialize logger
logger = structlog.get_logger(__name__)


# Load default config
def get_default_db_path() -> str:
    """Get default database path from config."""
    try:
        import os
        from pathlib import Path

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        config = get_config(config_dir)
        # Use data_storage.raw path as base directory for database
        return str(Path(config.data_storage.raw).parent / "ncaa_basketball.db")
    except Exception as e:
        logger.warning(f"Failed to load config for DB path: {e}. Using fallback path.")
        return "data/ncaa_basketball.db"


@dataclass
class TeamsIngestionConfig:
    """Configuration for teams data ingestion."""

    # API configuration
    espn_api_config: ESPNApiConfig

    # Data storage configuration - use empty string as placeholder,
    # will be filled from config if empty
    parquet_dir: str = ""

    # Season to fetch
    season: str = ""

    # Conference ID filter (optional)
    conference: str = ""

    # Pagination parameters
    limit: int = 100
    page: int = 1

    # Processing options
    force_update: bool = False

    def __post_init__(self):
        """Initialize default values from config if not provided."""
        if not self.parquet_dir:
            try:
                import os
                from pathlib import Path

                config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
                config = get_config(config_dir)
                self.parquet_dir = config.data_storage.raw
            except Exception as e:
                logger.warning(f"Failed to load config for parquet_dir: {e}. Using fallback path.")
                self.parquet_dir = "data/raw"


def fetch_teams(config: TeamsIngestionConfig) -> dict[str, Any]:
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


def fetch_teams_all_pages(config: TeamsIngestionConfig) -> dict[str, Any]:
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


def store_teams_data(config: TeamsIngestionConfig, data: dict[str, Any]) -> dict[str, Any]:
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
    conference: str | None = None,
    seasons: list[str] | None = None,
    espn_api_config: ESPNApiConfig | None = None,
    parquet_dir: str = "",
) -> list[str]:
    """Ingest team data for specified seasons.

    Args:
        conference: Conference ID to filter (optional)
        seasons: List of seasons to fetch (YYYY format)
        espn_api_config: ESPN API configuration
        parquet_dir: Directory for output Parquet files. If empty, uses config value.

    Returns:
        List of processed seasons
    """
    # Use default config if not provided
    if espn_api_config is None:
        import os
        from pathlib import Path

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        config = get_config(config_dir)
        espn_api_config = config.espn_api

        # Use config parquet_dir if not provided
        if not parquet_dir:
            parquet_dir = config.data_storage.raw

    # Determine which seasons to process
    if not seasons:
        import os
        from pathlib import Path

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        config = get_config(config_dir)

        current_season = config.seasons.current  # Season is now just YYYY

        # Check if we should include historical seasons
        include_historical = True  # Default to including historical seasons

        if include_historical:
            # Use the historical start season from config
            historical_start_season = config.historical.start_season

            # Generate all seasons between historical_start_season and current_season
            start_year = int(historical_start_season)
            end_year = int(current_season)

            seasons = []
            for year in range(start_year, end_year + 1):
                seasons.append(str(year))

            logger.info(f"Processing {len(seasons)} seasons from {start_year} to {end_year}")
        else:
            # Just use current season
            seasons = [current_season]
            logger.info(f"Processing current season: {current_season}")

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
            logger.error(f"Error processing season {season}: {e!s}")
            continue

    # Return list of successfully processed seasons
    return processed_seasons


class TeamsIngestion:
    def __init__(
        self,
        espn_api_config: ESPNApiConfig | dict[str, Any],
        db_path: str | None = None,
    ):
        """
        Initialize the TeamsIngestion class.

        Args:
            espn_api_config: Configuration for the ESPN API, either as an ESPNApiConfig object
                or a dictionary
            db_path: Path to the SQLite database. If None, uses config value.
        """
        # Handle both object and dictionary config formats for testing compatibility
        if isinstance(espn_api_config, dict):
            client_config = ClientAPIConfig(
                base_url=espn_api_config.get("base_url", ""),
                endpoints=espn_api_config.get("endpoints", {}),
                initial_request_delay=espn_api_config.get("initial_request_delay", 1.0),
                max_retries=espn_api_config.get("max_retries", 3),
                timeout=espn_api_config.get("timeout", 10),
                max_concurrency=espn_api_config.get("max_concurrency", 5),
                min_request_delay=espn_api_config.get("min_request_delay", 0.1),
                max_request_delay=espn_api_config.get("max_request_delay", 5.0),
                backoff_factor=espn_api_config.get("backoff_factor", 1.5),
                recovery_factor=espn_api_config.get("recovery_factor", 0.9),
                error_threshold=espn_api_config.get("error_threshold", 3),
                success_threshold=espn_api_config.get("success_threshold", 10),
            )
            self.historical_seasons = espn_api_config.get("historical", {}).get("seasons", [])
        else:
            # Handle new config structure with request_settings
            rs = espn_api_config.request_settings
            client_config = ClientAPIConfig(
                base_url=espn_api_config.base_url,
                endpoints=espn_api_config.endpoints,
                v3_base_url=getattr(espn_api_config, "v3_base_url", ""),
                initial_request_delay=rs.initial_request_delay,
                max_retries=rs.max_retries,
                timeout=rs.timeout,
                max_concurrency=rs.max_concurrency,
                min_request_delay=rs.min_request_delay,
                max_request_delay=rs.max_request_delay,
                backoff_factor=rs.backoff_factor,
                recovery_factor=rs.recovery_factor,
                error_threshold=rs.error_threshold,
                success_threshold=rs.success_threshold,
            )
            self.historical_seasons = (
                espn_api_config.historical.seasons if hasattr(espn_api_config, "historical") else []
            )

        self.api_client = ESPNApiClient(client_config)

        # Use provided db_path or get from config
        if db_path is None:
            db_path = get_default_db_path()

        self.db_path = db_path


def get_processed_seasons(db_path: str | None = None) -> list[str]:
    """Get list of seasons that have already been processed.

    Args:
        db_path: Path to the database. If None, uses config value.

    Returns:
        List of seasons in YYYY format
    """
    # Use provided db_path or get from config
    if db_path is None:
        db_path = get_default_db_path()

    # Use ParquetStorage to get processed seasons
    from src.utils.parquet_storage import ParquetStorage

    storage = ParquetStorage(base_dir=Path(db_path) / "raw")
    return storage.get_processed_seasons()
