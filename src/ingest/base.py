"""Base classes for ESPN API data ingestion.

This module provides the common foundation for ingesting data from
ESPN APIs into the bronze layer as Parquet files.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import structlog

from src.utils.config import ESPNApiConfig, get_config
from src.utils.espn_api_client import ESPNApiClient
from src.utils.parquet_storage import ParquetStorage

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class BaseIngestionConfig:
    """Base configuration for all data ingestion operations."""

    # API configuration
    espn_api_config: ESPNApiConfig

    # Data storage configuration
    parquet_dir: str = ""

    # Processing options
    force_check: bool = False  # Force API requests and check if data changed
    force_overwrite: bool = False  # Force overwrite existing data without checking

    # Concurrency options
    concurrency: int | None = None

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


# Type variable for the key used in the processed items list
T = TypeVar("T")


class BaseIngestion(Generic[T], ABC):
    """Abstract base class for all data ingestion implementations."""

    def __init__(
        self,
        config: BaseIngestionConfig,
    ) -> None:
        """Initialize base ingestion.

        Args:
            config: Ingestion configuration
        """
        self.config = config
        self.parquet_storage = ParquetStorage(base_dir=config.parquet_dir)

        # Initialize API client
        self.api_client = ESPNApiClient(config.espn_api_config)

        # Create semaphore for concurrency control
        max_concurrency = (
            config.concurrency
            if config.concurrency is not None
            else self.api_client.max_concurrency
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)

        logger.debug(
            f"Initialized {self.__class__.__name__}",
            parquet_dir=config.parquet_dir,
            force_check=config.force_check,
            force_overwrite=config.force_overwrite,
            max_concurrency=max_concurrency,
        )

    @abstractmethod
    async def fetch_item_async(self, item_key: T) -> dict[str, Any]:
        """Fetch data for a specific item asynchronously.

        Args:
            item_key: Key identifying the item to fetch

        Returns:
            The API response data
        """
        pass

    @abstractmethod
    async def store_item_async(self, item_key: T, data: dict[str, Any]) -> dict[str, Any]:
        """Store data for a specific item asynchronously.

        Args:
            item_key: Key identifying the item
            data: The data to store

        Returns:
            Result information
        """
        pass

    @abstractmethod
    def get_processed_items(self) -> list[T]:
        """Get list of items that have already been processed.

        Returns:
            List of processed item keys
        """
        pass

    @abstractmethod
    def determine_items_to_process(self) -> list[T]:
        """Determine which items to process based on configuration.

        Returns:
            List of item keys to process
        """
        pass

    async def process_item_async(self, item_key: T) -> dict[str, Any]:
        """Process a single item asynchronously.

        Args:
            item_key: Key identifying the item to process

        Returns:
            Processing result
        """
        try:
            async with self.semaphore:
                # Fetch data
                data = await self.fetch_item_async(item_key)

                # Store data
                result = await self.store_item_async(item_key, data)

                return {
                    "item_key": item_key,
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error(
                f"Error processing {item_key}",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "item_key": item_key,
                "success": False,
                "error": str(e),
            }

    async def process_items_async(self, item_keys: list[T]) -> dict[str, Any]:
        """Process multiple items asynchronously.

        Args:
            item_keys: List of item keys to process

        Returns:
            Processing results
        """
        if not item_keys:
            logger.warning("No items to process")
            return {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "items": [],
            }

        # Process all items concurrently
        tasks = [self.process_item_async(item_key) for item_key in item_keys]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Track statistics
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful

        logger.info(
            f"Processed {len(results)} items",
            successful=successful,
            failed=failed,
        )

        return {
            "processed": len(results),
            "successful": successful,
            "failed": failed,
            "items": results,
        }

    async def ingest_async(self) -> list[T]:
        """Run the ingestion process asynchronously.

        Returns:
            List of successfully processed item keys
        """
        # Determine items to process
        items_to_process = self.determine_items_to_process()

        if not items_to_process:
            logger.warning("No items to process")
            return []

        logger.info(f"Processing {len(items_to_process)} items")

        # Process items
        results = await self.process_items_async(items_to_process)

        # Extract successfully processed items
        successful_items = [r["item_key"] for r in results["items"] if r.get("success", False)]

        return successful_items

    def ingest(self) -> list[T]:
        """Run the ingestion process.

        Returns:
            List of successfully processed item keys
        """
        return asyncio.run(self.ingest_async())
