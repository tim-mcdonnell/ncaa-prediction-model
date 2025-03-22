"""Tests for pagination functionality in the base ingestion class.

This test suite verifies that the BaseIngestion class correctly handles pagination
for ESPN API endpoints, including fetching all pages and handling edge cases.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ingest.base import BaseIngestion, BaseIngestionConfig
from src.utils.config import ESPNApiConfig, RequestSettings


@pytest.fixture
def mock_espn_api_config():
    """Create a mock ESPN API configuration for testing."""
    return ESPNApiConfig(
        base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        v3_base_url="https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball",
        endpoints={
            "teams": "v3:/seasons/{season}/teams",
        },
        request_settings=RequestSettings(
            initial_request_delay=0.01,
            max_retries=1,
            timeout=1.0,
            max_concurrency=5,
        ),
    )


@pytest.fixture
def mock_api_data_first_page():
    """Create mock data for the first page of results."""
    return {
        "count": 150,
        "pageCount": 2,
        "pageIndex": 1,
        "pageSize": 100,
        "items": [{"id": str(i)} for i in range(1, 101)],  # 100 items
    }


@pytest.fixture
def mock_api_data_second_page():
    """Create mock data for the second page of results."""
    return {
        "count": 150,
        "pageCount": 2,
        "pageIndex": 2,
        "pageSize": 100,
        "items": [{"id": str(i)} for i in range(101, 151)],  # 50 items
    }


@pytest.fixture
def mock_api_data_full_last_page():
    """Create mock data for the second page of results when it's completely full."""
    return {
        "count": 200,
        "pageCount": 2,
        "pageIndex": 2,
        "pageSize": 100,
        "items": [{"id": str(i)} for i in range(101, 201)],  # 100 items (full page)
    }


@pytest.fixture
def mock_api_data_empty_page():
    """Create mock data for an empty page."""
    return {
        "count": 100,
        "pageCount": 2,
        "pageIndex": 2,
        "pageSize": 100,
        "items": [],  # Empty items list
    }


@pytest.fixture
def mock_api_client(mock_api_data_first_page, mock_api_data_second_page):
    """Create a mock API client for testing."""
    mock_client = MagicMock()
    mock_client._request_async = AsyncMock()

    # Configure the mock to return different responses based on page parameter
    async def mock_request(url, params=None):
        if params and params.get("page") == 2:
            return mock_api_data_second_page
        return mock_api_data_first_page

    mock_client._request_async.side_effect = mock_request
    mock_client.get_endpoint_url = MagicMock(return_value="https://api.espn.com/v1/teams")

    return mock_client


# Create a concrete implementation of BaseIngestion for testing
class TestPaginationIngestion(BaseIngestion[str]):
    """Concrete implementation of BaseIngestion for testing pagination."""

    def __init__(self, config):
        """Initialize with test configuration."""
        super().__init__(config)
        self.test_items = []

    async def fetch_item_async(self, item_key: str) -> dict:
        """Mock implementation of abstract method."""
        # This will be overridden in tests
        return {}

    async def store_item_async(self, item_key: str, data: dict) -> dict:
        """Mock implementation of abstract method."""
        return {"success": True, "file_path": f"{item_key}.parquet"}

    def get_processed_items(self) -> list[str]:
        """Mock implementation of abstract method."""
        return []

    def determine_items_to_process(self) -> list[str]:
        """Mock implementation of abstract method."""
        return ["test_item"]


class TestPagination:
    """Tests for pagination functionality in BaseIngestion."""

    @pytest.mark.asyncio
    async def test_fetch_all_pages_async_with_multiple_pages_returns_all_items(
        self,
        mock_espn_api_config,
        mock_api_client,
        mock_api_data_first_page,
        mock_api_data_second_page,
    ):
        """Test that fetch_all_pages_async correctly combines items from all pages."""
        # Arrange
        config = BaseIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = TestPaginationIngestion(config)
        ingestion.api_client = mock_api_client
        endpoint = "teams"
        params = {"season": "2023"}

        # Act
        # This will fail initially as fetch_all_pages_async doesn't exist yet
        result = await ingestion.fetch_all_pages_async(endpoint, params)

        # Assert
        assert result["count"] == 150
        assert len(result["items"]) == 150  # Total from both pages

        # Check that both pages were requested
        assert mock_api_client._request_async.call_count == 2

        # Verify the first page has items 1-100 and second page has 101-150
        assert result["items"][0]["id"] == "1"
        assert result["items"][99]["id"] == "100"
        assert result["items"][100]["id"] == "101"
        assert result["items"][149]["id"] == "150"

    @pytest.mark.asyncio
    async def test_fetch_all_pages_async_with_full_last_page_fetches_additional_page(
        self,
        mock_espn_api_config,
        mock_api_client,
        mock_api_data_first_page,
        mock_api_data_full_last_page,
    ):
        """Test that an additional page is fetched when the last page is full."""
        # Arrange
        config = BaseIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = TestPaginationIngestion(config)
        ingestion.api_client = mock_api_client

        # Configure mock to return full second page and then empty third page
        async def mock_request(url, params=None):
            if params and params.get("page") == 2:
                return mock_api_data_full_last_page
            elif params and params.get("page") == 3:
                return {"count": 200, "pageCount": 2, "pageIndex": 3, "pageSize": 100, "items": []}
            return mock_api_data_first_page

        mock_api_client._request_async.side_effect = mock_request

        endpoint = "teams"
        params = {"season": "2023"}

        # Act
        # This will fail initially as fetch_all_pages_async doesn't exist yet
        result = await ingestion.fetch_all_pages_async(endpoint, params)

        # Assert
        assert result["count"] == 200
        assert len(result["items"]) == 200  # Total from both full pages

        # Check that three pages were requested (including verification page)
        assert mock_api_client._request_async.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_all_pages_async_handles_empty_page_response(
        self,
        mock_espn_api_config,
        mock_api_client,
        mock_api_data_first_page,
        mock_api_data_empty_page,
    ):
        """Test that fetch_all_pages_async handles empty page responses gracefully."""
        # Arrange
        config = BaseIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = TestPaginationIngestion(config)
        ingestion.api_client = mock_api_client

        # Configure mock to return empty second page
        async def mock_request(url, params=None):
            if params and params.get("page") == 2:
                return mock_api_data_empty_page
            return mock_api_data_first_page

        mock_api_client._request_async.side_effect = mock_request

        endpoint = "teams"
        params = {"season": "2023"}

        # Act
        # This will fail initially as fetch_all_pages_async doesn't exist yet
        result = await ingestion.fetch_all_pages_async(endpoint, params)

        # Assert
        assert result["count"] == 100  # Only count from first page should be used
        assert len(result["items"]) == 100  # Only items from first page

        # Check that two pages were requested
        assert mock_api_client._request_async.call_count == 2

    @pytest.mark.asyncio
    async def test_pagination_config_is_used_correctly(self, mock_espn_api_config, mock_api_client):
        """Test that pagination settings from config are applied correctly."""
        # Arrange
        # Add pagination settings to the endpoint config
        mock_api_client.endpoints = {
            "teams": {
                "pagination": {
                    "limit": 50  # Custom limit from config
                }
            }
        }

        # Configure the mock to return expected response and capture params
        params_captured = []

        async def mock_request(url, params=None):
            if params:
                params_captured.append(params)
            return {
                "count": 150,
                "pageCount": 2,
                "pageIndex": 1,
                "pageSize": 50,  # Should match the limit from config
                "items": [{"id": str(i)} for i in range(1, 51)],
            }

        mock_api_client._request_async.side_effect = mock_request

        config = BaseIngestionConfig(espn_api_config=mock_espn_api_config)
        ingestion = TestPaginationIngestion(config)
        ingestion.api_client = mock_api_client

        endpoint = "teams"
        params = {"season": "2023"}

        # Act
        # We don't use the result in this test, just checking the call parameters
        await ingestion.fetch_all_pages_async(endpoint, params)

        # Assert
        # Verify the mock was called
        assert mock_api_client._request_async.call_count >= 1

        # Check that the params capture includes a call with limit=50
        assert len(params_captured) > 0

        # Find the first page parameters (which should have limit=50)
        first_page_params = next((p for p in params_captured if p.get("page", 0) == 1), None)
        if not first_page_params:
            first_page_params = params_captured[0]  # Fallback

        # Verify correct limit was applied from config
        assert first_page_params["limit"] == 50
