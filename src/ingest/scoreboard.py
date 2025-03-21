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

    # Data storage configuration
    parquet_dir: str = "data/raw"

    # Legacy DB path - only used for reading processed dates during migration
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

    # Processing options
    force_update: bool = False  # Force update even for existing dates


def get_existing_dates(db: Database) -> list[str]:
    """Get already processed dates from the database.

    Args:
        db: Database connection

    Returns:
        List of dates already in the database in YYYY-MM-DD format
    """
    return db.get_processed_dates()


class ScoreboardIngestion:
    """Scoreboard data ingestion from ESPN API."""

    def __init__(
        self: "ScoreboardIngestion",
        espn_api_config: ESPNApiConfig | dict,
        db_path: str = "data/ncaa.duckdb",
        skip_existing: bool = False,
        parquet_dir: str = "data/raw",
        force_update: bool = False,
    ) -> None:
        """Initialize scoreboard ingestion.

        Args:
            espn_api_config: ESPN API configuration (object or dict)
            db_path: Path to DuckDB database (only used for reading processed dates
                during migration)
            skip_existing: Whether to skip dates that are already in the database
            parquet_dir: Base directory for Parquet files
            force_update: Force update even for existing dates
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
            max_concurrency = espn_api_config.get("max_concurrency", 5)
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
            self.batch_size = getattr(espn_api_config, "batch_size", 10)
            max_concurrency = getattr(espn_api_config, "max_concurrency", 5)

        self.db_path = db_path
        self.skip_existing = skip_existing
        self.parquet_dir = parquet_dir
        self.force_update = force_update

        # Create semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrency)

        logger.debug(
            "Initialized scoreboard ingestion",
            batch_size=self.batch_size,
            db_path=self.db_path,
            parquet_dir=self.parquet_dir,
            force_update=self.force_update,
            max_concurrency=max_concurrency,
        )

    def fetch_and_store_date(
        self: "ScoreboardIngestion",
        date: str,
        db: Database = None,  # Legacy parameter, not used
    ) -> dict[str, Any]:
        """Fetch and store scoreboard data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            db: Legacy parameter, not used for Parquet storage

        Returns:
            The API response data
        """
        logger.info("Fetching scoreboard data for date", date=date)

        # Format date for ESPN API
        espn_date = format_date_for_api(date)

        # Fetch data
        data = self.api_client.fetch_scoreboard(date=espn_date)

        # Store in Parquet
        from src.utils.parquet_storage import ParquetStorage

        parquet_storage = ParquetStorage(base_dir=self.parquet_dir)
        result = parquet_storage.write_scoreboard_data(
            date=date,
            source_url=f"{self.api_client.get_endpoint_url('scoreboard')}",
            parameters={"dates": espn_date, "groups": "50", "limit": 200},
            data=data,
        )

        # Log if data was unchanged (only when not force updating)
        if not self.force_update and result.get("unchanged", False):
            logger.info("Data unchanged for date - no update needed", date=date)

        return data

    async def fetch_and_store_date_async(
        self: "ScoreboardIngestion",
        date: str,
        db: Database = None,  # Legacy parameter, not used
    ) -> dict[str, Any]:
        """Fetch and store scoreboard data for a specific date asynchronously.

        Args:
            date: Date in YYYY-MM-DD format
            db: Legacy parameter, not used for Parquet storage

        Returns:
            The API response data
        """
        async with self.semaphore:  # Limit concurrent requests
            logger.info("Asynchronously fetching scoreboard data for date", date=date)

            # Format date for ESPN API
            espn_date = format_date_for_api(date)

            # Fetch data using the async method
            data = await self.api_client.fetch_scoreboard_async(date=espn_date)

            # Store in Parquet (uses synchronous method since filesystem operations)
            from src.utils.parquet_storage import ParquetStorage

            parquet_storage = ParquetStorage(base_dir=self.parquet_dir)

            # Create parameters for the write operation
            write_params = {
                "date": date,
                "source_url": f"{self.api_client.get_endpoint_url('scoreboard')}",
                "parameters": {"dates": espn_date, "groups": "50", "limit": 200},
                "data": data,
            }

            # Run the write operation in an executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: parquet_storage.write_scoreboard_data(**write_params)
            )

            # Log if data was unchanged (only when not force updating)
            if not self.force_update and result.get("unchanged", False):
                logger.info("Data unchanged for date - no update needed", date=date)

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
        # Create a database connection to pass to the async method
        return asyncio.run(self.process_date_range_async(dates))

    async def process_date_range_async(
        self, dates: list[str], concurrency: int | None = None, batch_size: int | None = None
    ) -> list[str]:
        """Process a list of dates asynchronously.

        Args:
            dates: List of dates to process
            concurrency: Optional concurrency limit override
            batch_size: Optional batch size override

        Returns:
            List of processed dates
        """
        if concurrency is not None:
            # Update semaphore if concurrency is specified
            self.semaphore = asyncio.Semaphore(concurrency)
            logger.debug("Updated concurrency limit", concurrency=concurrency)

        # Respect skip_existing if not forcing updates
        dates_to_process = dates
        processed_dates: list[str] = []

        # If we're not forcing updates, filter out dates we've already processed
        if self.skip_existing and not self.force_update:
            existing_dates = set(self.get_existing_dates())
            dates_to_process = [date for date in dates if date not in existing_dates]

            logger.info(
                "Dates to process",
                count=len(dates_to_process),
                total_dates=len(dates),
                already_processed=len(dates) - len(dates_to_process),
            )
        elif self.force_update:
            logger.info(
                "Force update enabled - processing all dates",
                count=len(dates_to_process),
                total_dates=len(dates),
            )
        else:
            logger.info(
                "Dates to process",
                count=len(dates_to_process),
                total_dates=len(dates),
            )

        # Use specified batch size or default
        actual_batch_size = batch_size if batch_size is not None else self.batch_size
        total_dates = len(dates_to_process)
        total_processed = 0
        total_successful = 0
        total_failed = 0
        all_errors = []

        # Process in batches with improved error handling
        for i in range(0, total_dates, actual_batch_size):
            batch_end_idx = min(i + actual_batch_size, total_dates)
            batch = dates_to_process[i:batch_end_idx]
            batch_start = batch[0] if batch else ""
            batch_end = batch[-1] if batch else ""

            logger.info(
                "Processing batch asynchronously",
                batch_start=batch_start,
                batch_end=batch_end,
                batch_size=len(batch),
            )

            try:
                # Use our improved batch processing method
                batch_result = await self.process_batch_async(batch)

                # Update statistics
                batch_successful = batch_result.get("successful", 0)
                batch_failed = batch_result.get("failed", 0)
                batch_errors = batch_result.get("errors", [])

                total_successful += batch_successful
                total_failed += batch_failed
                total_processed += batch_successful + batch_failed
                all_errors.extend(batch_errors)

                # Add successful dates to the processed list
                # Since we don't have direct access to which dates succeeded,
                # use the count of successful operations
                if batch_successful > 0:
                    error_dates = set(error["date"] for error in batch_errors if "date" in error)
                    for date in batch:
                        if date not in error_dates:
                            processed_dates.append(date)

                logger.info(
                    "Completed batch",
                    batch_start=batch_start,
                    batch_end=batch_end,
                    successful=batch_successful,
                    failed=batch_failed,
                )
            except Exception as e:
                # This should not happen with our new process_batch_async method,
                # but keep as an extra safety measure
                logger.error(
                    "Unexpected critical error during batch processing",
                    batch_start=batch_start,
                    batch_end=batch_end,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                total_failed += len(batch)
                total_processed += len(batch)
                all_errors.append({"error": str(e), "batch": f"{batch_start} to {batch_end}"})

        logger.info(
            "Completed processing date range",
            processed=total_processed,
            total=total_dates,
            successful=total_successful,
            failed=total_failed,
            error_count=len(all_errors),
        )

        return processed_dates

    def get_existing_dates(self: "ScoreboardIngestion", db: Database = None) -> list[str]:
        """Get dates that have already been processed.

        Args:
            db: Optional database connection (will create one if not provided)

        Returns:
            List of dates in YYYY-MM-DD format
        """
        from src.utils.parquet_storage import ParquetStorage

        parquet_storage = ParquetStorage(base_dir=self.parquet_dir)
        return parquet_storage.get_processed_dates(endpoint="scoreboard")

    async def process_batch_async(self, batch: list[str], db: Database = None) -> dict[str, Any]:
        """Process a batch of dates asynchronously with improved error handling.

        Args:
            batch: List of dates to process
            db: Optional database connection

        Returns:
            Dictionary with successful and failed counts
        """
        successful = 0
        failed = 0
        errors = []

        # Process all dates in the batch concurrently
        batch_tasks = []
        for date in batch:
            # Creating a database connection is not needed for Parquet storage
            # but we pass it for backward compatibility
            task = self.fetch_and_store_date_async(date, db if db else Database(self.db_path))
            batch_tasks.append(task)

        # Wait for all batch tasks to complete
        try:
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
                    failed += 1
                    errors.append({"date": date, "error": str(result)})
                else:
                    successful += 1
        except Exception as e:
            logger.error(
                "Critical error during batch processing",
                error=str(e),
                error_type=type(e).__name__,
            )
            # If we can't even complete the gathering, count all as failed
            failed = len(batch)
            errors.append({"error": str(e), "batch_size": len(batch)})

        return {"successful": successful, "failed": failed, "errors": errors}


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
        historical_start = config.espn_api_config.historical_start_date
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
    # Determine dates to process
    dates_to_process = _determine_dates_to_process(config)

    if not dates_to_process:
        logger.warning("No dates to process")
        return []

    # Initialize ingestion
    ingestion = ScoreboardIngestion(
        espn_api_config=config.espn_api_config,
        db_path=config.db_path,  # Kept for backward compatibility
        skip_existing=True,  # Always skip existing to support incremental ingestion
        parquet_dir=config.parquet_dir,
        force_update=config.force_update,
    )

    # Configure concurrency
    concurrency = None
    if config.concurrency is not None:
        # Explicit concurrency override
        concurrency = config.concurrency
        logger.info("Using explicit concurrency setting", concurrency=concurrency)
    elif config.cautious:
        # Conservative concurrency for stable operation
        concurrency = max(1, ingestion.api_client.config.max_concurrency // 2)
        logger.info("Using cautious concurrency setting", concurrency=concurrency)
    elif config.aggressive:
        # Aggressive concurrency for faster ingestion (may trigger rate limits)
        concurrency = ingestion.api_client.config.max_concurrency * 2
        logger.info("Using aggressive concurrency setting", concurrency=concurrency)

    # Process dates asynchronously with configured concurrency
    processed_dates = await ingestion.process_date_range_async(
        dates_to_process, concurrency=concurrency
    )

    return processed_dates


def ingest_scoreboard(config: ScoreboardIngestionConfig) -> list[str]:
    """Process scoreboard data ingestion.

    Args:
        config: Ingestion configuration

    Returns:
        List of processed dates
    """
    # Run the async version in a new event loop
    return asyncio.run(ingest_scoreboard_async(config))


# For backward compatibility with existing code
def ingest_scoreboard_legacy(
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
