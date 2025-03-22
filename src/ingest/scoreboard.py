"""ESPN Scoreboard data ingestion module for NCAA basketball games.

This module contains functionality for fetching and storing basketball scoreboard data
from the ESPN API, including game scores, teams, and other game-related information.
It supports various date-based fetching strategies including specific dates, date ranges,
yesterday/today, and entire seasons.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

from src.ingest.base import BaseIngestion, BaseIngestionConfig
from src.utils.config import get_config
from src.utils.date_utils import (
    format_date_for_api,
    get_date_range,
    get_season_date_range,
    get_today,
    get_yesterday,
)

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class ScoreboardIngestionConfig(BaseIngestionConfig):
    """Configuration for scoreboard data ingestion."""

    # Date selection parameters (only one should be used)
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    yesterday: bool = False
    today: bool = False
    seasons: list[str] | None = None
    year: int | None = None


class ScoreboardIngestion(BaseIngestion[str]):
    """Scoreboard data ingestion from ESPN API."""

    def __init__(
        self,
        config: ScoreboardIngestionConfig,
    ) -> None:
        """Initialize scoreboard ingestion.

        Args:
            config: Scoreboard ingestion configuration
        """
        super().__init__(config)
        self.config = config  # Type hint as ScoreboardIngestionConfig

    async def fetch_item_async(self, date: str) -> dict[str, Any]:
        """Fetch scoreboard data for a specific date asynchronously.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            The API response data
        """
        logger.info("Fetching scoreboard data for date", date=date)

        # Format date for ESPN API
        espn_date = format_date_for_api(date)

        # Fetch data using the async method
        data = await self.api_client.fetch_scoreboard_async(date=espn_date)

        return data

    async def store_item_async(self, date: str, data: dict[str, Any]) -> dict[str, Any]:
        """Store scoreboard data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            data: The data to store

        Returns:
            Result information
        """
        # Format date for ESPN API
        espn_date = format_date_for_api(date)

        # Create parameters for the write operation
        write_params = {
            "date": date,
            "source_url": f"{self.api_client.get_endpoint_url('scoreboard')}",
            "parameters": {"dates": espn_date, "groups": "50", "limit": 200},
            "data": data,
            "force_overwrite": self.config.force_overwrite,
        }

        # Run the write operation
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: self.parquet_storage.write_scoreboard_data(**write_params)
        )

        # Log if data was unchanged (only when not force overwriting)
        if not self.config.force_overwrite and result.get("unchanged", False):
            logger.info("Data unchanged for date - no update needed", date=date)

        return result

    def get_processed_items(self) -> list[str]:
        """Get dates that have already been processed.

        Returns:
            List of dates in YYYY-MM-DD format
        """
        return self.parquet_storage.get_processed_dates(endpoint="scoreboard")

    def determine_items_to_process(self) -> list[str]:
        """Determine which dates to process based on provided parameters.

        Returns:
            List of dates to process
        """
        all_dates = _determine_dates_to_process(self.config)

        # If neither force_check nor force_overwrite is enabled, skip already processed dates
        if not self.config.force_check and not self.config.force_overwrite:
            processed_dates = set(self.get_processed_items())
            filtered_dates = [date for date in all_dates if date not in processed_dates]

            if len(all_dates) != len(filtered_dates):
                logger.info(
                    "Filtered out already processed dates",
                    total=len(all_dates),
                    to_process=len(filtered_dates),
                    skipped=len(all_dates) - len(filtered_dates),
                )

            return filtered_dates

        return all_dates


def _determine_dates_to_process(config: ScoreboardIngestionConfig) -> list[str]:
    """Determine which dates to process based on provided parameters.

    Args:
        config: Configuration for scoreboard ingestion

    Returns:
        List of dates to process

    Raises:
        ValueError: If no dates are determined
    """
    dates_to_process = []

    if config.date:
        dates_to_process.append(config.date)
    elif config.start_date and config.end_date:
        dates_to_process = get_date_range(config.start_date, config.end_date)
    elif config.seasons:
        for season in config.seasons:
            season_start, season_end = get_season_date_range(season)
            season_dates = get_date_range(season_start, season_end)
            dates_to_process.extend(season_dates)
    elif config.yesterday:
        dates_to_process.append(get_yesterday())
    elif config.today:
        dates_to_process.append(get_today())
    elif config.year:
        start = f"{config.year}-01-01"
        end = f"{config.year}-12-31"
        dates_to_process = get_date_range(start, end)
    else:
        yesterday_date = get_yesterday()
        # Get historical start date from the appropriate configuration
        import os
        from pathlib import Path

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        config_obj = get_config(config_dir)
        historical_start = config_obj.historical.get_start_date()

        if historical_start:
            dates_to_process = get_date_range(historical_start, yesterday_date)

    if not dates_to_process:
        logger.error("No dates specified for ingestion")
        error_msg = "No dates specified for ingestion"
        raise ValueError(error_msg)

    # Sort dates and remove duplicates
    return sorted(set(dates_to_process))


async def ingest_scoreboard_async(config: ScoreboardIngestionConfig) -> list[str]:
    """Process scoreboard data ingestion asynchronously.

    Args:
        config: Ingestion configuration

    Returns:
        List of processed dates
    """
    # Initialize ingestion
    ingestion = ScoreboardIngestion(config)

    # Run ingestion
    return await ingestion.ingest_async()


def ingest_scoreboard(config: ScoreboardIngestionConfig) -> list[str]:
    """Process scoreboard data ingestion.

    Args:
        config: Ingestion configuration

    Returns:
        List of processed dates
    """
    # Run the async version in a new event loop
    return asyncio.run(ingest_scoreboard_async(config))
