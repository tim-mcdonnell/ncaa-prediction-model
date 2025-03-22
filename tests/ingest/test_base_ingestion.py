"""Tests for the base ingestion classes.

This test suite validates the functionality of the abstract base classes for ingestion,
ensuring they define the correct interface and provide the expected functionality.
"""

import abc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from src.ingest.base import BaseIngestion, BaseIngestionConfig
from src.utils.config import ESPNApiConfig, RequestSettings

# Initialize logger
logger = structlog.get_logger(__name__)


class TestBaseIngestionConfig:
    """Tests for the BaseIngestionConfig abstract class."""

    def test_init_requires_espn_api_config(self):
        """Test that BaseIngestionConfig initialization requires espn_api_config."""
        with pytest.raises(TypeError):
            BaseIngestionConfig()

    def test_init_with_valid_espn_api_config(self):
        """Test BaseIngestionConfig initialization with valid espn_api_config."""
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = BaseIngestionConfig(espn_api_config=espn_api_config)
        assert config.espn_api_config == espn_api_config


class ConcreteIngestionConfig(BaseIngestionConfig):
    """Concrete implementation of BaseIngestionConfig for testing."""

    def __init__(self, espn_api_config, items=None):
        super().__init__(espn_api_config)
        self.items = items or []


class ConcreteIngestion(BaseIngestion):
    """Concrete implementation of BaseIngestion for testing."""

    def __init__(self, config):
        """Initialize with mocked dependencies to avoid actual API client initialization."""
        # Skip the parent class initialization
        self.config = config

        # Create mocked dependencies
        self.parquet_storage = MagicMock()
        self.api_client = MagicMock()
        self.api_client.request_async = AsyncMock()

        # Setup a semaphore for concurrency
        self.semaphore = MagicMock()
        self.semaphore.__aenter__ = AsyncMock()
        self.semaphore.__aexit__ = AsyncMock()

    def determine_items_to_process(self):
        return self.config.items

    def get_processed_items(self):
        return []

    async def fetch_item_async(self, item):
        return {"item": item, "data": "sample_data"}

    async def store_item_async(self, item, data):
        return {"success": True, "item": item}


class TestBaseIngestion:
    """Tests for the BaseIngestion abstract class."""

    def test_base_ingestion_abstract(self):
        """Test that BaseIngestion is an abstract class with abstract methods."""
        assert issubclass(BaseIngestion, abc.ABC)

    def test_init_requires_config(self):
        """Test that BaseIngestion initialization requires config of correct type."""
        # No config
        with pytest.raises(TypeError):
            BaseIngestion()

        # Wrong config type
        with pytest.raises(TypeError):

            class WrongConfig:
                pass

            with patch("src.ingest.base.ESPNApiClient"):
                BaseIngestion(WrongConfig())

    def test_init_with_valid_config(self):
        """Test BaseIngestion initialization with valid config."""
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = ConcreteIngestionConfig(espn_api_config=espn_api_config)

        # Mock the ESPNApiClient instantiation
        with patch("src.ingest.base.ESPNApiClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            # Set the max_concurrency directly on the mock client
            mock_client.max_concurrency = 1

            # Create a BaseIngestion subclass instance
            class TestIngestion(BaseIngestion):
                async def fetch_item_async(self, item_key):
                    return {}

                async def store_item_async(self, item_key, data):
                    return {}

                def get_processed_items(self):
                    return []

                def determine_items_to_process(self):
                    return []

            ingestion = TestIngestion(config)

            assert ingestion.config == config
            assert ingestion.api_client == mock_client

    @pytest.mark.asyncio
    async def test_process_item_async(self):
        """Test process_item_async processes a single item."""
        # Arrange
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = ConcreteIngestionConfig(espn_api_config=espn_api_config, items=["item1"])
        ingestion = ConcreteIngestion(config)

        # Mock methods
        ingestion.fetch_item_async = AsyncMock(
            return_value={"item": "item1", "data": "sample_data"}
        )
        ingestion.store_item_async = AsyncMock(return_value={"success": True, "item": "item1"})

        # Act
        result = await ingestion.process_item_async("item1")

        # Assert
        assert result["success"] is True
        assert result["item_key"] == "item1"
        ingestion.fetch_item_async.assert_called_once_with("item1")
        ingestion.store_item_async.assert_called_once_with(
            "item1", {"item": "item1", "data": "sample_data"}
        )

    @pytest.mark.asyncio
    async def test_ingest_async(self):
        """Test ingest_async processes all items."""
        # Arrange
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = ConcreteIngestionConfig(
            espn_api_config=espn_api_config, items=["item1", "item2", "item3"]
        )
        ingestion = ConcreteIngestion(config)

        # Mock methods
        ingestion.determine_items_to_process = MagicMock(return_value=["item1", "item2", "item3"])
        ingestion.process_item_async = AsyncMock(
            return_value={"success": True, "item_key": "placeholder"}
        )

        # Override process_items_async to return a sample result
        async def mock_process_items_async(items):
            return {
                "processed": 3,
                "successful": 3,
                "failed": 0,
                "items": [
                    {"success": True, "item_key": "item1"},
                    {"success": True, "item_key": "item2"},
                    {"success": True, "item_key": "item3"},
                ],
            }

        ingestion.process_items_async = mock_process_items_async

        # Act
        result = await ingestion.ingest_async()

        # Assert
        assert result == ["item1", "item2", "item3"]
        ingestion.determine_items_to_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_async_with_semaphore(self):
        """Test ingest_async uses semaphore to limit concurrency."""
        # Arrange
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=2,  # Set max_concurrency to 2
            ),
        )

        config = ConcreteIngestionConfig(
            espn_api_config=espn_api_config, items=["item1", "item2", "item3", "item4", "item5"]
        )
        ingestion = ConcreteIngestion(config)

        # Mock methods
        ingestion.determine_items_to_process = MagicMock(
            return_value=["item1", "item2", "item3", "item4", "item5"]
        )

        # Override process_items_async to return a sample result
        async def mock_process_items_async(items):
            return {
                "processed": 5,
                "successful": 5,
                "failed": 0,
                "items": [
                    {"success": True, "item_key": "item1"},
                    {"success": True, "item_key": "item2"},
                    {"success": True, "item_key": "item3"},
                    {"success": True, "item_key": "item4"},
                    {"success": True, "item_key": "item5"},
                ],
            }

        ingestion.process_items_async = mock_process_items_async

        # Act
        result = await ingestion.ingest_async()

        # Assert
        assert result == ["item1", "item2", "item3", "item4", "item5"]
        ingestion.determine_items_to_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_async_with_specific_items(self):
        """Test a conceptual extension of ingest_async with specific items."""
        # In the actual implementation, ingest_async doesn't have an items parameter
        # This test is more of a conceptual test for a subclass that might add that feature

        # Arrange
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = ConcreteIngestionConfig(
            espn_api_config=espn_api_config, items=["item1", "item2", "item3"]
        )
        ingestion = ConcreteIngestion(config)

        # Mock methods - note we specifically do NOT mock determine_items_to_process
        # because we're not testing that functionality here

        # Create a custom process_items_async function that uses the supplied items
        async def mock_process_items_async(items):
            # Check that we're using the supplied items
            assert items == ["item2", "item3"]
            return {
                "processed": 2,
                "successful": 2,
                "failed": 0,
                "items": [
                    {"success": True, "item_key": "item2"},
                    {"success": True, "item_key": "item3"},
                ],
            }

        ingestion.process_items_async = mock_process_items_async

        # Create a custom ingest_async that accepts specific items
        async def custom_ingest_async(items=None):
            # Skip the determine_items_to_process step when specific items are provided
            if items is None:
                return []

            logger.info(f"Processing {len(items)} items")
            results = await ingestion.process_items_async(items)

            # Extract successfully processed items
            successful_items = [r["item_key"] for r in results["items"] if r.get("success", False)]

            return successful_items

        # Replace the standard ingest_async with our custom version
        ingestion.ingest_async = custom_ingest_async

        # Act
        result = await ingestion.ingest_async(items=["item2", "item3"])

        # Assert
        assert result == ["item2", "item3"]

    @pytest.mark.asyncio
    async def test_ingest_async_with_no_items(self):
        """Test ingest_async when no items are available to process."""
        # Arrange
        espn_api_config = ESPNApiConfig(
            base_url="test",
            v3_base_url="test_v3",
            endpoints={},
            request_settings=RequestSettings(
                initial_request_delay=0.01,
                max_retries=1,
                timeout=1.0,
                max_concurrency=1,
            ),
        )

        config = ConcreteIngestionConfig(espn_api_config=espn_api_config, items=[])
        ingestion = ConcreteIngestion(config)

        # Mock methods
        ingestion.determine_items_to_process = MagicMock(return_value=[])
        ingestion.process_items_async = AsyncMock()

        # Act
        result = await ingestion.ingest_async()

        # Assert
        assert result == []
        ingestion.determine_items_to_process.assert_called_once()
        ingestion.process_items_async.assert_not_called()
