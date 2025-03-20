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

    # Concurrency options
    concurrency: int | None = None
    aggressive: bool = False
    cautious: bool = False


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
            self.api_client = ESPNApiClient(client_config)
            self.batch_size = espn_api_config.get("batch_size", 10)
        else:
            client_config = ClientAPIConfig(
                base_url=espn_api_config.base_url,
                endpoints=espn_api_config.endpoints,
                initial_request_delay=espn_api_config.initial_request_delay,
                max_retries=espn_api_config.max_retries,
                timeout=espn_api_config.timeout,
                max_concurrency=espn_api_config.max_concurrency,
                min_request_delay=espn_api_config.min_request_delay,
                max_request_delay=espn_api_config.max_request_delay,
                backoff_factor=espn_api_config.backoff_factor,
                recovery_factor=espn_api_config.recovery_factor,
                error_threshold=espn_api_config.error_threshold,
                success_threshold=espn_api_config.success_threshold,
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

    async def fetch_and_store_date_async(
        self: "ScoreboardIngestion",
        date: str,
        db: Database,
    ) -> dict[str, Any]:
        """Asynchronously fetch and store scoreboard data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            db: Database connection

        Returns:
            The API response data
        """
        logger.info("Asynchronously fetching scoreboard data for date", date=date)

        # Format date for ESPN API
        espn_date = format_date_for_api(date)

        # Fetch data asynchronously
        data = await self.api_client.fetch_scoreboard_async(date=espn_date)

        # Store in database (database writes are sequential to avoid concurrency issues)
        db.insert_bronze_scoreboard(
            date=date,
            url=f"{self.api_client.get_endpoint_url('scoreboard')}",
            params={"dates": espn_date, "groups": "50", "limit": 200},
            data=data,
        )

        return data

    def process_date_range(self: "ScoreboardIngestion", dates: list[str]) -> list[str]:
        """Process a range of dates in batches.

        Note: This method is maintained for backward compatibility.
        New code should use process_date_range_async for better performance.

        Args:
            dates: List of dates in YYYY-MM-DD format

        Returns:
            List of processed dates
        """
        # For backward compatibility, run the async version in a new event loop
        return asyncio.run(self.process_date_range_async(dates))

    async def process_date_range_async(self: "ScoreboardIngestion", dates: list[str]) -> list[str]:
        """Process a range of dates asynchronously in batches.

        Args:
            dates: List of dates in YYYY-MM-DD format

        Returns:
            List of processed dates
        """
        logger.info(
            "Processing date range asynchronously",
            start=dates[0],
            end=dates[-1],
            total_dates=len(dates),
        )

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
        processed_dates = []
        for i in range(0, len(dates_to_process), self.batch_size):
            batch = dates_to_process[i : i + self.batch_size]
            logger.info(
                "Processing batch asynchronously",
                batch_start=batch[0],
                batch_end=batch[-1],
                batch_size=len(batch),
            )

            # Use Database context manager for each batch
            with Database(self.db_path) as db:
                # Process all dates in the batch concurrently
                batch_tasks = []
                for date in batch:
                    task = self.fetch_and_store_date_async(date, db)
                    batch_tasks.append(task)

                # Wait for all batch tasks to complete
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Check for any errors and log them
                for date, result in zip(batch, batch_results, strict=False):
                    if isinstance(result, Exception):
                        logger.error(
                            "Error processing date",
                            date=date,
                            error=str(result),
                            error_type=type(result).__name__,
                        )
                    else:
                        processed_dates.append(date)

            logger.info(
                "Completed batch",
                batch_start=batch[0],
                batch_end=batch[-1],
                successful=len([r for r in batch_results if not isinstance(r, Exception)]),
                failed=len([r for r in batch_results if isinstance(r, Exception)]),
            )

        logger.info(
            "Completed processing date range",
            processed=len(processed_dates),
            total=len(dates_to_process),
        )
        return processed_dates


async def ingest_scoreboard_async(config: ScoreboardIngestionConfig) -> list[str]:
    """Asynchronously ingest scoreboard data from ESPN API.

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

    # Create API config with potential concurrency overrides
    api_config = config.espn_api_config

    # Override concurrency settings if specified
    if config.concurrency is not None:
        api_config.max_concurrency = config.concurrency
        logger.info("Overriding max concurrency", value=config.concurrency)

    # Apply aggressive or cautious settings
    if config.aggressive:
        api_config.min_request_delay = 0.05
        api_config.initial_request_delay = 0.1
        api_config.recovery_factor = 0.8
        logger.info("Using aggressive request settings for faster processing")
    elif config.cautious:
        api_config.initial_request_delay = max(api_config.initial_request_delay, 1.0)
        api_config.backoff_factor = 2.0
        api_config.max_concurrency = min(api_config.max_concurrency, 3)
        logger.info("Using cautious request settings for reliability")

    # Create ingestion instance
    ingestion = ScoreboardIngestion(api_config, config.db_path)

    # Run the process
    logger.info(
        "Starting async scoreboard ingestion",
        date_count=len(dates_to_process),
        start_date=dates_to_process[0],
        end_date=dates_to_process[-1],
        max_concurrency=api_config.max_concurrency,
    )

    processed_dates = await ingestion.process_date_range_async(dates_to_process)

    logger.info("Completed async scoreboard ingestion", date_count=len(processed_dates))

    return processed_dates


def ingest_scoreboard(config: ScoreboardIngestionConfig) -> list[str]:
    """Ingest scoreboard data from ESPN API.

    Args:
        config: Configuration for scoreboard ingestion

    Returns:
        List of dates that were processed

    Raises:
        ValueError: If no dates are specified or if ESPN API configuration is missing
    """
    # Use async version but run it in a new event loop
    return asyncio.run(ingest_scoreboard_async(config))


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
