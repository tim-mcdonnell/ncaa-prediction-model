"""ESPN Scoreboard data ingestion module for NCAA basketball games.

This module contains functionality for fetching and storing basketball scoreboard data
from the ESPN API, including game scores, teams, and other game-related information.
It supports various date-based fetching strategies including specific dates, date ranges,
yesterday/today, and entire seasons.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from src.utils.config import ESPNApiConfig
from src.utils.database import Database
from src.utils.date_utils import (
    format_date_for_api,
    get_date_range,
    get_season_date_range,
    get_today,
    get_yesterday,
)
from src.utils.espn_api_client import ESPNApiClient
from src.utils.espn_api_client import ESPNApiConfig as ClientAPIConfig

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class ScoreboardIngestionConfig:
    """Configuration for scoreboard data ingestion."""

    # API configuration
    espn_api_config: ESPNApiConfig

    # Database configuration
    db_path: str = "data/ncaa.duckdb"

    # Date selection parameters (only one should be used)
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    yesterday: bool = False
    today: bool = False
    seasons: list[str] | None = None
    year: int | None = None


class ScoreboardIngestion:
    """Scoreboard data ingestion from ESPN API."""

    def __init__(
        self: "ScoreboardIngestion",
        espn_api_config: ESPNApiConfig | dict,
        db_path: str = "data/ncaa.duckdb",
    ) -> None:
        """Initialize scoreboard ingestion.

        Args:
            espn_api_config: ESPN API configuration (object or dict)
            db_path: Path to DuckDB database
        """
        # Handle both object and dictionary config formats for testing compatibility
        if isinstance(espn_api_config, dict):
            client_config = ClientAPIConfig(
                base_url=espn_api_config.get("base_url", ""),
                endpoints=espn_api_config.get("endpoints", {}),
                request_delay=espn_api_config.get("request_delay", 1.0),
                max_retries=espn_api_config.get("max_retries", 3),
                timeout=espn_api_config.get("timeout", 10),
            )
            self.api_client = ESPNApiClient(client_config)
            self.batch_size = espn_api_config.get("batch_size", 10)
        else:
            client_config = ClientAPIConfig(
                base_url=espn_api_config.base_url,
                endpoints=espn_api_config.endpoints,
                request_delay=espn_api_config.request_delay,
                max_retries=espn_api_config.max_retries,
                timeout=espn_api_config.timeout,
            )
            self.api_client = ESPNApiClient(client_config)
            self.batch_size = espn_api_config.batch_size

        self.db_path = db_path

        logger.debug(
            "Initialized scoreboard ingestion",
            db_path=db_path,
            batch_size=self.batch_size,
        )

    def fetch_and_store_date(
        self: "ScoreboardIngestion",
        date: str,
        db: Database,
    ) -> dict[str, Any]:
        """Fetch and store scoreboard data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            db: Database connection

        Returns:
            The API response data
        """
        logger.info("Fetching scoreboard data for date", date=date)

        # Format date for ESPN API
        espn_date = format_date_for_api(date)

        # Fetch data
        data = self.api_client.fetch_scoreboard(date=espn_date)

        # Store in database
        db.insert_bronze_scoreboard(
            date=date,
            url=f"{self.api_client.get_endpoint_url('scoreboard')}",
            params={"dates": espn_date, "groups": "50", "limit": 200},
            data=data,
        )

        return data

    def process_date_range(self: "ScoreboardIngestion", dates: list[str]) -> list[str]:
        """Process a range of dates in batches.

        Args:
            dates: List of dates in YYYY-MM-DD format

        Returns:
            List of processed dates
        """
        logger.info("Processing date range", start=dates[0], end=dates[-1], total_dates=len(dates))

        # Get already processed dates
        with Database(self.db_path) as db:
            processed_dates = set(db.get_processed_dates())

        # Filter out already processed dates
        dates_to_process = [d for d in dates if d not in processed_dates]

        if not dates_to_process:
            logger.info("All dates already processed", total_dates=len(dates))
            return []

        logger.info(
            "Dates to process",
            count=len(dates_to_process),
            total_dates=len(dates),
            already_processed=len(dates) - len(dates_to_process),
        )

        # Process in batches
        for i in range(0, len(dates_to_process), self.batch_size):
            batch = dates_to_process[i : i + self.batch_size]
            logger.info(
                "Processing batch",
                batch_start=batch[0],
                batch_end=batch[-1],
                batch_size=len(batch),
            )

            # Use Database context manager for each batch
            with Database(self.db_path) as db:
                # Process dates in the batch
                for date in batch:
                    self.fetch_and_store_date(date, db)

            logger.info("Completed batch", batch_start=batch[0], batch_end=batch[-1])

        return dates_to_process


def ingest_scoreboard(config: ScoreboardIngestionConfig) -> list[str]:
    """Ingest scoreboard data from ESPN API.

    Args:
        config: Configuration for scoreboard ingestion

    Returns:
        List of dates that were processed

    Raises:
        ValueError: If no dates are specified or if ESPN API configuration is missing
    """
    if config.espn_api_config is None:
        error_msg = "ESPN API configuration is required"
        raise ValueError(error_msg)

    # Initialize dates list
    dates_to_process = []

    # Determine which dates to process based on provided parameters
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
        historical_start = config.espn_api_config.historical_start_date
        if historical_start:
            dates_to_process = get_date_range(historical_start, yesterday_date)

    if not dates_to_process:
        logger.error("No dates specified for ingestion")
        error_msg = "No dates specified for ingestion"
        raise ValueError(error_msg)

    # Sort dates and remove duplicates
    dates_to_process = sorted(set(dates_to_process))

    # Create ingestion instance
    ingestion = ScoreboardIngestion(config.espn_api_config, config.db_path)

    # Run the process
    logger.info(
        "Starting scoreboard ingestion",
        date_count=len(dates_to_process),
        start_date=dates_to_process[0],
        end_date=dates_to_process[-1],
    )

    processed_dates = ingestion.process_date_range(dates_to_process)

    logger.info("Completed scoreboard ingestion", date_count=len(processed_dates))

    return processed_dates


# For backward compatibility with existing code
def ingest_scoreboard_legacy(  # noqa: PLR0913
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    yesterday: bool = False,
    today: bool = False,
    seasons: list[str] | None = None,
    year: int | None = None,
    espn_api_config: ESPNApiConfig | None = None,
    db_path: str = "data/ncaa.duckdb",
) -> list[str]:
    """Legacy interface for scoreboard ingestion.

    Note: This function is maintained for backward compatibility.
    New code should use the ingest_scoreboard function with ScoreboardIngestionConfig.

    Only one date selection parameter should be used. Precedence (high to low):
    1. date
    2. start_date & end_date
    3. yesterday/today
    4. seasons
    5. year

    Args:
        date: Specific date to ingest in YYYY-MM-DD format
        start_date: Start date for date range in YYYY-MM-DD format
        end_date: End date for date range in YYYY-MM-DD format
        yesterday: Ingest data for yesterday
        today: Ingest data for today
        seasons: List of seasons in YYYY-YY format
        year: Calendar year to ingest
        espn_api_config: ESPN API configuration
        db_path: Path to DuckDB database

    Returns:
        List of dates that were processed
    """
    if espn_api_config is None:
        # Load default configuration if none provided
        import os
        from pathlib import Path

        from src.utils.config import get_config  # Local import to avoid circular imports

        config_dir = Path(os.environ.get("CONFIG_DIR", "config"))
        config_obj = get_config(config_dir)
        espn_api_config = config_obj.espn_api

    config = ScoreboardIngestionConfig(
        espn_api_config=espn_api_config,
        db_path=db_path,
        date=date,
        start_date=start_date,
        end_date=end_date,
        yesterday=yesterday,
        today=today,
        seasons=seasons,
        year=year,
    )

    return ingest_scoreboard(config)
