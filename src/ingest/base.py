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

    # Default pagination settings
    default_page_limit: int = 100
    default_page_param: str = "page"
    default_limit_param: str = "limit"

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

    async def fetch_all_pages_async(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch all pages of data from a paginated API endpoint.

        This method handles pagination automatically, fetching all available pages and
        combining the results. It also verifies completeness by checking if the last page
        is full and fetching an additional page if needed.

        Args:
            endpoint: The API endpoint to query
            params: Additional parameters to include in the request

        Returns:
            Combined data from all pages with items from all pages merged
        """
        # Initialize params if None
        if params is None:
            params = {}

        # Get endpoint-specific pagination configuration
        endpoint_config = self._get_endpoint_pagination_config(endpoint)

        # Set up pagination parameters
        page_param = endpoint_config.get("page_param", self.config.default_page_param)
        limit_param = endpoint_config.get("limit_param", self.config.default_limit_param)
        page_limit = endpoint_config.get("limit", self.config.default_page_limit)

        # Create a copy of params with pagination settings
        page_params = params.copy()
        page_params[limit_param] = page_limit
        page_params[page_param] = 1

        # Fetch first page
        url = self.api_client.get_endpoint_url(endpoint, **params)
        first_page = await self.api_client._request_async(url, page_params)

        # Check if multiple pages exist
        total_pages = first_page.get("pageCount", 1)

        # If only one page, return immediately
        if total_pages <= 1:
            logger.debug("Only one page of data available", endpoint=endpoint)
            return first_page

        # Initialize with first page data
        all_data = {
            "count": first_page.get("count", 0),
            "pageIndex": 1,
            "pageSize": first_page.get("pageSize", page_limit),
            "pageCount": total_pages,
            "items": first_page.get("items", []),
        }

        logger.debug(
            "Fetching additional pages",
            endpoint=endpoint,
            total_pages=total_pages,
            items_count_so_far=len(all_data["items"]),
        )

        # Create tasks for remaining pages
        remaining_tasks = []
        for page in range(2, total_pages + 1):
            # Create a new params dict for each page
            page_params = params.copy()
            page_params[limit_param] = page_limit
            page_params[page_param] = page

            # Create task to fetch the page
            task = self._fetch_page_async(endpoint, page_params)
            remaining_tasks.append(task)

        # Fetch all remaining pages concurrently
        remaining_results = await asyncio.gather(*remaining_tasks, return_exceptions=True)

        # Process results and add to combined data
        for i, result in enumerate(remaining_results):
            page_num = i + 2  # Page numbers start from 2

            if isinstance(result, Exception):
                logger.error(
                    "Failed to fetch page",
                    endpoint=endpoint,
                    page=page_num,
                    error=str(result),
                )
                continue

            # Update count from the last valid page response
            if "count" in result:
                all_data["count"] = result["count"]

            # Add items to combined result
            all_data["items"].extend(result.get("items", []))

        # Check if the last page is full (containing exactly page_limit items)
        # If so, we need to fetch one more page to ensure we have all the data
        last_page_result = None
        for result in reversed(remaining_results):
            if not isinstance(result, Exception) and "items" in result:
                last_page_result = result
                break

        if last_page_result and len(last_page_result.get("items", [])) == page_limit:
            logger.debug(
                "Last page is full, fetching verification page",
                endpoint=endpoint,
                last_page=total_pages,
                items_in_last_page=len(last_page_result.get("items", [])),
            )

            # Fetch one more page to verify we have all data
            verification_page_params = params.copy()
            verification_page_params[limit_param] = page_limit
            verification_page_params[page_param] = total_pages + 1

            try:
                verification_page = await self._fetch_page_async(endpoint, verification_page_params)
                verification_items = verification_page.get("items", [])

                if verification_items:
                    # There was more data, add it to our results
                    all_data["items"].extend(verification_items)

                    # Update count if provided in the verification page
                    if "count" in verification_page:
                        all_data["count"] = verification_page["count"]
                    else:
                        # Otherwise update count to match the actual number of items
                        all_data["count"] = len(all_data["items"])

                    logger.info(
                        "Found additional items in verification page",
                        endpoint=endpoint,
                        additional_items=len(verification_items),
                    )
            except Exception as e:
                logger.warning(
                    "Failed to fetch verification page",
                    endpoint=endpoint,
                    page=total_pages + 1,
                    error=str(e),
                )

        # Ensure count matches the actual number of items if empty pages were returned
        if all_data["count"] != len(all_data["items"]):
            # For empty page responses, update count to match actual items
            if any(isinstance(r, dict) and not r.get("items", []) for r in remaining_results):
                all_data["count"] = len(all_data["items"])

        logger.info(
            "Fetched all pages successfully",
            endpoint=endpoint,
            total_pages=total_pages,
            total_items=len(all_data["items"]),
        )

        return all_data

    async def _fetch_page_async(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch a single page of data from an API endpoint.

        Args:
            endpoint: The API endpoint to query
            params: Parameters to include in the request, including pagination params

        Returns:
            The API response data for the requested page
        """
        url = self.api_client.get_endpoint_url(
            endpoint,
            **{
                k: v
                for k, v in params.items()
                if not k.startswith("page") and not k.startswith("limit")
            },
        )

        logger.debug(
            "Fetching page",
            endpoint=endpoint,
            url=url,
            params=params,
        )

        try:
            response = await self.api_client._request_async(url, params)
            logger.debug(
                "Fetched page successfully",
                endpoint=endpoint,
                page=params.get(self.config.default_page_param, 1),
                item_count=len(response.get("items", [])),
            )
            return response
        except Exception as e:
            logger.error(
                "Failed to fetch page",
                endpoint=endpoint,
                params=params,
                error=str(e),
            )
            raise

    def _get_endpoint_pagination_config(self, endpoint: str) -> dict[str, Any]:
        """Get pagination configuration for a specific endpoint.

        Retrieves endpoint-specific pagination settings from the API configuration,
        falling back to default values if not specified.

        Args:
            endpoint: The API endpoint name

        Returns:
            Dictionary with pagination configuration for the endpoint
        """
        # Try to get endpoint configuration
        endpoints = self.api_client.endpoints

        # Check if endpoints is a dictionary with nested configuration
        if isinstance(endpoints, dict) and endpoint in endpoints:
            endpoint_config = endpoints[endpoint]
            if isinstance(endpoint_config, dict) and "pagination" in endpoint_config:
                return endpoint_config["pagination"]

        # No endpoint-specific pagination config found, return empty dict
        return {}

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
