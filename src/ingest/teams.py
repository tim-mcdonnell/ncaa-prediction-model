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

        # We need to fetch all pages for this season
        return await self._fetch_all_pages_async(season)

    async def _fetch_page_async(self, season: str, page: int) -> dict[str, Any]:
        """Fetch a single page of team data for a season asynchronously.

        Args:
            season: Season in YYYY format
            page: Page number

        Returns:
            The API response data
        """
        # Build URL parameters
        params = {
            "limit": self.config.limit,
            "page": page,
        }

        # Add conference filter if specified
        if self.config.conference:
            params["groups"] = self.config.conference

        # Build URL
        url = self.api_client.get_endpoint_url("teams", season=season)

        # Make request
        logger.debug(
            "Fetching teams data page",
            url=url,
            season=season,
            conference=self.config.conference if self.config.conference else "all",
            page=page,
            limit=self.config.limit,
        )

        try:
            response = await self.api_client._request_async(url, params)
            logger.debug(
                "Fetched teams data page successfully",
                season=season,
                page=page,
                count=response.get("count", 0),
            )
            return response
        except Exception as e:
            logger.error(
                "Failed to fetch teams data page",
                season=season,
                page=page,
                error=str(e),
            )
            raise

    async def _fetch_all_pages_async(self, season: str) -> dict[str, Any]:
        """Fetch all pages of team data for a season asynchronously.

        Args:
            season: Season in YYYY format

        Returns:
            Combined data from all pages
        """
        # Fetch first page
        first_page = await self._fetch_page_async(season, 1)

        # Extract pagination info
        total_pages = first_page.get("pageCount", 1)

        # If only one page, return immediately
        if total_pages <= 1:
            return first_page

        # Initialize with first page data
        all_teams = {
            "count": first_page.get("count", 0),
            "pageIndex": 1,
            "pageSize": first_page.get("pageSize", self.config.limit),
            "pageCount": total_pages,
            "items": first_page.get("items", []),
        }

        # Create tasks for remaining pages
        remaining_tasks = []
        for page in range(2, total_pages + 1):
            task = self._fetch_page_async(season, page)
            remaining_tasks.append(task)

        # Fetch all remaining pages
        remaining_results = await asyncio.gather(*remaining_tasks, return_exceptions=True)

        # Process results and add to combined data
        for i, result in enumerate(remaining_results):
            page_num = i + 2  # Page numbers start from 2

            if isinstance(result, Exception):
                logger.error(
                    "Failed to fetch page",
                    season=season,
                    page=page_num,
                    error=str(result),
                )
                continue

            # Add items to combined result
            all_teams["items"].extend(result.get("items", []))

        logger.info(
            "Fetched all team pages",
            season=season,
            total_pages=total_pages,
            total_teams=len(all_teams["items"]),
        )

        return all_teams

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
        all_seasons = _determine_seasons_to_process(self.config)

        # If neither force_check nor force_overwrite is enabled, skip already processed seasons
        if not self.config.force_check and not self.config.force_overwrite:
            processed_seasons = set(self.get_processed_items())
            filtered_seasons = [season for season in all_seasons if season not in processed_seasons]

            if len(all_seasons) != len(filtered_seasons):
                logger.info(
                    "Filtered out already processed seasons",
                    total=len(all_seasons),
                    to_process=len(filtered_seasons),
                    skipped=len(all_seasons) - len(filtered_seasons),
                )

            return filtered_seasons

        return all_seasons


def _determine_seasons_to_process(config: TeamsIngestionConfig) -> list[str]:
    """Determine which seasons to process based on configuration.

    Args:
        config: Teams ingestion configuration

    Returns:
        List of seasons to process in YYYY format
    """
    if config.seasons:
        return config.seasons

    # Use config to determine seasons
    import os
    from pathlib import Path

    config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
    config_obj = get_config(config_dir)

    current_season = config_obj.seasons.current  # Season is now just YYYY

    # Check if we should include historical seasons
    include_historical = True  # Default to including historical seasons

    if include_historical:
        # Use the historical start season from config
        historical_start_season = config_obj.historical.start_season

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

    return seasons


async def ingest_teams_async(config: TeamsIngestionConfig) -> list[str]:
    """Process teams data ingestion asynchronously.

    Args:
        config: Ingestion configuration

    Returns:
        List of processed seasons
    """
    # Initialize ingestion
    ingestion = TeamsIngestion(config)

    # Run ingestion
    return await ingestion.ingest_async()


def ingest_teams(config: TeamsIngestionConfig) -> list[str]:
    """Process teams data ingestion.

    Args:
        config: Ingestion configuration

    Returns:
        List of processed seasons
    """
    # Run the async version in a new event loop
    return asyncio.run(ingest_teams_async(config))
