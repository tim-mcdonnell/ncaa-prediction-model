"""Unified ingestion module for all ESPN data endpoints.

This module provides high-level functions for ingesting data from multiple ESPN API
endpoints with unified configuration and concurrency management.
"""

import asyncio
from dataclasses import dataclass

import structlog

from src.ingest.base import BaseIngestionConfig
from src.ingest.scoreboard import ScoreboardIngestionConfig, ingest_scoreboard_async
from src.ingest.teams import TeamsIngestionConfig, ingest_teams_async

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class UnifiedIngestionConfig(BaseIngestionConfig):
    """Configuration for unified multi-endpoint ingestion."""

    # Endpoints to ingest
    endpoints: list[str] = None

    # Specific endpoint configurations
    # For scoreboard
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    yesterday: bool = False
    today: bool = False
    year: int | None = None

    # For teams and season-based endpoints
    seasons: list[str] | None = None

    # Filter options
    conference: str | None = None

    # Global concurrency control
    max_parallel_endpoints: int = 2


async def ingest_multiple_endpoints(
    config: UnifiedIngestionConfig,
) -> dict[str, list[str]]:
    """Ingest data from multiple ESPN API endpoints.

    Args:
        config: Unified ingestion configuration

    Returns:
        Dictionary mapping endpoint names to lists of processed items
    """
    # Get valid endpoints
    valid_endpoints = get_valid_endpoints()

    # Filter requested endpoints to valid ones
    endpoints_to_process = []

    if not config.endpoints:
        logger.warning("No endpoints specified, defaulting to all")
        endpoints_to_process = list(valid_endpoints)
    else:
        for endpoint in config.endpoints:
            if endpoint == "all":
                endpoints_to_process = list(valid_endpoints)
                break

            if endpoint in valid_endpoints:
                endpoints_to_process.append(endpoint)
            else:
                logger.warning(f"Unknown endpoint: {endpoint}, skipping")

    if not endpoints_to_process:
        logger.error("No valid endpoints to process")
        return {}

    # Create tasks for each endpoint
    tasks = {}
    for endpoint in endpoints_to_process:
        if endpoint == "scoreboard":
            endpoint_config = create_scoreboard_config(config)
            tasks[endpoint] = ingest_scoreboard_async(endpoint_config)
        elif endpoint == "teams":
            endpoint_config = create_teams_config(config)
            tasks[endpoint] = ingest_teams_async(endpoint_config)
        # Add other endpoints here as they're implemented

    # Define the maximum number of endpoints to run in parallel
    max_parallel = config.max_parallel_endpoints

    # Process endpoints in parallel with concurrency limit
    results = {}
    endpoint_groups = [
        list(tasks.keys())[i : i + max_parallel] for i in range(0, len(tasks), max_parallel)
    ]

    for group in endpoint_groups:
        group_tasks = {endpoint: tasks[endpoint] for endpoint in group}
        group_results = await asyncio.gather(*group_tasks.values(), return_exceptions=True)

        # Map results back to endpoints
        for endpoint, result in zip(group_tasks.keys(), group_results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    f"Error processing endpoint {endpoint}",
                    error=str(result),
                    error_type=type(result).__name__,
                )
                results[endpoint] = []
            else:
                results[endpoint] = result
                logger.info(
                    f"Successfully processed endpoint {endpoint}",
                    processed_count=len(result),
                )

    return results


def ingest_all(config: UnifiedIngestionConfig) -> dict[str, list[str]]:
    """Run ingestion for multiple endpoints.

    Args:
        config: Unified ingestion configuration

    Returns:
        Dictionary mapping endpoint names to lists of processed items
    """
    return asyncio.run(ingest_multiple_endpoints(config))


def get_valid_endpoints() -> set[str]:
    """Get set of valid endpoint names.

    Returns:
        Set of valid endpoint names
    """
    # This will grow as more endpoints are implemented
    return {"scoreboard", "teams"}


def create_scoreboard_config(config: UnifiedIngestionConfig) -> ScoreboardIngestionConfig:
    """Create a scoreboard-specific configuration from unified config.

    Args:
        config: Unified configuration

    Returns:
        Scoreboard-specific configuration
    """
    return ScoreboardIngestionConfig(
        espn_api_config=config.espn_api_config,
        parquet_dir=config.parquet_dir,
        date=config.date,
        start_date=config.start_date,
        end_date=config.end_date,
        yesterday=config.yesterday,
        today=config.today,
        seasons=config.seasons,
        year=config.year,
        force_check=config.force_check,
        force_overwrite=config.force_overwrite,
        concurrency=config.concurrency,
    )


def create_teams_config(config: UnifiedIngestionConfig) -> TeamsIngestionConfig:
    """Create a teams-specific configuration from unified config.

    Args:
        config: Unified configuration

    Returns:
        Teams-specific configuration
    """
    return TeamsIngestionConfig(
        espn_api_config=config.espn_api_config,
        parquet_dir=config.parquet_dir,
        seasons=config.seasons,
        conference=config.conference,
        force_check=config.force_check,
        force_overwrite=config.force_overwrite,
        concurrency=config.concurrency,
    )
