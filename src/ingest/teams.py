"""ESPN Basketball Teams API data ingestion module.

This module contains functionality for fetching and storing NCAA basketball team data
from the ESPN API, including team metadata, colors, and status information.
It supports fetching both current and historical team data across multiple seasons.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

from src.ingest.base import BaseIngestion, BaseIngestionConfig
from src.utils.config import get_config

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
class TeamsIngestionConfig(BaseIngestionConfig):
    """Configuration for teams data ingestion."""

    # Season parameters
    seasons: list[str] | None = None

    # Optional filters
    conference: str | None = None

    # Pagination parameters
    limit: int = 100
    page: int = 1


class TeamsIngestion(BaseIngestion[str]):
    """Teams data ingestion from ESPN API."""

    def __init__(
        self,
        config: TeamsIngestionConfig,
    ) -> None:
        """Initialize teams ingestion.

        Args:
            config: Teams ingestion configuration
        """
        super().__init__(config)
        self.config = config  # Type hint as TeamsIngestionConfig

    async def fetch_item_async(self, season: str) -> dict[str, Any]:
        """Fetch teams data for a specific season asynchronously.

        Args:
            season: Season in YYYY format

        Returns:
            The API response data
        """
        logger.info("Fetching teams data for season", season=season)

        # Use the base class pagination handling
        params = {"season": season}

        # Add conference filter if specified
        if self.config.conference:
            params["groups"] = self.config.conference

        # Fetch all pages using the base class method
        return await self.fetch_all_pages_async("teams", params)

    async def store_item_async(self, season: str, data: dict[str, Any]) -> dict[str, Any]:
        """Store teams data for a specific season.

        Args:
            season: Season in YYYY format
            data: The data to store

        Returns:
            Result information
        """
        # Build API URL for metadata
        source_url = self.api_client.get_endpoint_url("teams", season=season)

        # Create parameters object
        parameters = {
            "season": season,
            "limit": self.config.limit,
        }
        if self.config.conference:
            parameters["conference"] = self.config.conference

        # Store data
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.parquet_storage.write_team_data(
                source_url=source_url,
                parameters=parameters,
                data=data,
                force_overwrite=self.config.force_overwrite,
            ),
        )

        if result.get("success", False):
            logger.info(
                "Stored team data successfully",
                season=season,
                file_path=result.get("file_path", ""),
                team_count=len(data.get("items", [])),
            )
        else:
            logger.error(
                "Failed to store team data",
                season=season,
                error=result.get("error", "Unknown error"),
            )

        return result

    def get_processed_items(self) -> list[str]:
        """Get seasons that have already been processed.

        Returns:
            List of seasons in YYYY format
        """
        return self.parquet_storage.get_processed_seasons(endpoint="teams")

    def determine_items_to_process(self) -> list[str]:
        """Determine which seasons to process based on configuration.

        Returns:
            List of seasons to process
        """
        return _determine_seasons_to_process(self.config)


def _determine_seasons_to_process(config: TeamsIngestionConfig) -> list[str]:
    """Determine which seasons to process based on configuration.

    Args:
        config: Teams ingestion configuration

    Returns:
        List of seasons to process
    """
    # If specific seasons are provided, use those
    if config.seasons:
        logger.info(f"Using {len(config.seasons)} seasons from configuration")
        return config.seasons

    # Otherwise, try to load from global config
    try:
        import os
        from pathlib import Path

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        global_config = get_config(config_dir)

        # Get current season from global config
        current_season = global_config.seasons.current
        if not current_season:
            logger.warning("No current season found in configuration, using default")
            current_season = "2023"  # Default to 2023 if not specified

        # Get historical start season
        historical_start = global_config.historical.start_season

        # Generate range of seasons
        all_seasons = []
        for year in range(int(historical_start), int(current_season) + 1):
            all_seasons.append(str(year))

        logger.info(
            f"Determined {len(all_seasons)} seasons from configuration",
            start=historical_start,
            end=current_season,
        )
        return all_seasons
    except Exception as e:
        # Fallback to only current season
        logger.warning(f"Failed to determine seasons from configuration: {e}")
        return ["2023"]  # Default to 2023 if configuration fails


async def ingest_teams_async(config: TeamsIngestionConfig) -> list[str]:
    """Run teams ingestion process asynchronously.

    Args:
        config: Teams ingestion configuration

    Returns:
        List of successfully processed teams
    """
    ingest = TeamsIngestion(config)
    return await ingest.ingest_async()


def ingest_teams(config: TeamsIngestionConfig) -> list[str]:
    """Run teams ingestion process.

    Args:
        config: Teams ingestion configuration

    Returns:
        List of successfully processed teams
    """
    return asyncio.run(ingest_teams_async(config))
