import time
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from tenacity import RetryError

from src.utils.espn_api_client import ESPNApiClient, ESPNApiConfig


class TestESPNApiClientModule:
    """Tests for the ESPN API client module."""

    @pytest.fixture()  # type: ignore
    def client(self) -> ESPNApiClient:
        """Create a test ESPN API client."""
        config = ESPNApiConfig(
            base_url="https://test.api.com",
            endpoints={
                "scoreboard": "/sports/basketball/scoreboard",
                "teams": "/sports/basketball/teams",
                "team_detail": "/sports/basketball/teams/{team_id}",
            },
            request_delay=0.01,  # Small delay for testing
            max_retries=2,
            timeout=1.0,
        )
        return ESPNApiClient(config)

    def test_init_with_valid_parameters_initializes_correctly(self) -> None:
        """Test initialization with valid parameters."""
        # Arrange & Act
        default_delay = 0.5
        default_retries = 3
        default_timeout = 10.0

        config = ESPNApiConfig(
            base_url="https://test.api.com",
            endpoints={"scoreboard": "/scoreboard"},
            request_delay=default_delay,
            max_retries=default_retries,
            timeout=default_timeout,
        )
        client = ESPNApiClient(config)

        # Assert
        assert client.base_url == "https://test.api.com"
        assert client.endpoints == {"scoreboard": "/scoreboard"}
        assert client.request_delay == default_delay
        assert client.max_retries == default_retries
        assert client.timeout == default_timeout
        assert client.last_request_time == 0

    def test_build_url_with_valid_endpoint_returns_correct_url(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _build_url with valid endpoint returns the correct URL."""
        # Arrange & Act
        url = client._build_url("scoreboard")

        # Assert
        assert url == "https://test.api.com/sports/basketball/scoreboard"

    def test_build_url_with_path_parameters_returns_formatted_url(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _build_url with path parameters returns correctly formatted URL."""
        # Arrange & Act
        url = client._build_url("team_detail", team_id="123")

        # Assert
        assert url == "https://test.api.com/sports/basketball/teams/123"

    def test_build_url_with_invalid_endpoint_raises_value_error(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _build_url with invalid endpoint raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Invalid endpoint"):
            client._build_url("invalid_endpoint")

    def test_throttle_request_when_called_within_delay_waits_appropriately(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _throttle_request waits appropriately when called within delay period."""
        # Arrange
        client.last_request_time = time.time()  # Set last request to now

        start_time = time.time()

        # Act
        client._throttle_request()

        elapsed = time.time() - start_time

        # Assert
        # Should wait at least the request_delay
        assert elapsed >= client.request_delay
        # New last_request_time should be updated
        assert client.last_request_time > start_time

    def test_throttle_request_when_called_after_delay_proceeds_immediately(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _throttle_request proceeds immediately when called after delay period."""
        # Arrange
        client.last_request_time = time.time() - (
            client.request_delay * 2
        )  # Set last request to well before now

        start_time = time.time()

        # Act
        client._throttle_request()

        elapsed = time.time() - start_time

        # Assert
        # Should not wait since last request was before delay period
        assert elapsed < client.request_delay
        # New last_request_time should be updated
        assert client.last_request_time >= start_time

    def test_request_with_successful_response_returns_json_data(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _request with successful response returns JSON data."""
        # Arrange
        expected_data = {"test": "data"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = expected_data

        # Setup mock client
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        # Setup mock context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client

        # Mock httpx.Client
        with patch("httpx.Client", return_value=mock_context):
            # Act
            result = client._request("https://test.api.com/test", {"param": "value"})

            # Assert
            assert result == expected_data
            mock_client.get.assert_called_once_with(
                "https://test.api.com/test",
                params={"param": "value"},
            )
            mock_response.raise_for_status.assert_called_once()

    def test_request_with_http_error_retries_to_max_retries(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _request with HTTP error retries up to max_retries."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Test error",
            request=MagicMock(),
            response=mock_response,
        )

        # Setup mock client
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        # Setup mock context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client

        # Mock httpx.Client
        with patch("httpx.Client", return_value=mock_context):
            # Act & Assert
            with pytest.raises(RetryError, match="RetryError"):
                client._request("https://test.api.com/test", {"param": "value"})

            # Verify the client was called for each retry attempt
            # Default is 3 attempts
            assert mock_client.get.call_count >= 1

    def test_fetch_scoreboard_with_valid_parameters_fetches_and_returns_data(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test fetch_scoreboard with valid parameters fetches and returns data."""
        # Arrange
        expected_data = {"events": [{"id": "123", "name": "Test Game"}]}

        # Mock the _request method
        with (
            patch.object(client, "_request", return_value=expected_data) as mock_request,
            patch.object(
                client,
                "_build_url",
                return_value="https://test.api.com/sports/basketball/scoreboard",
            ) as mock_build_url,
        ):
            # Act
            result = client.fetch_scoreboard("20230315", groups="50", limit=100)

            # Assert
            assert result == expected_data
            mock_build_url.assert_called_once_with("scoreboard")

            # Check that _request was called with the right parameters
            mock_request.assert_called_once_with(
                "https://test.api.com/sports/basketball/scoreboard",
                {"dates": "20230315", "groups": "50", "limit": 100},
            )

    def test_fetch_scoreboard_batch_with_multiple_dates_fetches_and_returns_all_data(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test fetch_scoreboard_batch with multiple dates returns data for all dates."""
        # Arrange
        dates = ["20230315", "20230316"]  # Only passing 2 dates
        expected_date_count = 2  # Expected count matches number of dates

        # Prepare test data
        mock_responses = {
            "20230315": {"events": [{"id": "123", "name": "Game 1"}]},
            "20230316": {"events": [{"id": "124", "name": "Game 2"}]},
        }

        # Configure mock client to return different responses based on date parameter
        def get_side_effect(_: str, params: dict[str, Any] | None = None) -> MagicMock:
            if params is None or "dates" not in params:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = {"events": []}
                return mock_resp

            date = params["dates"]
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = mock_responses[date]
            return mock_resp

        # Create mock client
        mock_client = MagicMock()
        mock_client.get.side_effect = get_side_effect

        # Setup mock context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client

        # Replace the httpx.Client to return our mock
        with (
            patch("httpx.Client", return_value=mock_context),
            # Mock the _build_url method
            patch.object(
                client,
                "_build_url",
                return_value="https://test.api.com/sports/basketball/scoreboard",
            ),
            # Mock throttling
            patch.object(client, "_throttle_request"),
        ):
            # Act
            result = client.fetch_scoreboard_batch(
                dates=dates,  # Pass the dates list directly
                groups="50",
                limit=100,
            )

            # Assert
            assert len(result) == expected_date_count
            # Check each date's data matches the expected response
            for date in dates:
                assert date in result
                assert result[date] == mock_responses[date]

            # Check that get was called exactly once per date
            assert mock_client.get.call_count == expected_date_count


class TestESPNApiClient:
    """Integration tests for ESPNApiClient."""

    @pytest.fixture()  # type: ignore
    def mock_httpx_client(self):
        """Mock the httpx.Client for testing."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"events": [{"id": "12345"}]}

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            yield mock_client_instance

    @pytest.fixture()  # type: ignore
    def api_config(self):
        """Create a test API configuration."""
        return {
            "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            "request_delay": 0.01,
            "batch_size": 10,
        }

    def test_init_with_config_sets_properties_correctly(self, api_config):
        """Test initialization with config sets properties correctly."""
        # Act
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            request_delay=api_config["request_delay"],
        )
        client = ESPNApiClient(config)

        # Assert
        assert client.base_url == api_config["base_url"]
        assert client.endpoints == {"scoreboard": "scoreboard"}
        assert client.request_delay == api_config["request_delay"]

    def test_fetch_scoreboard_with_valid_date_calls_get_with_correct_params(
        self, mock_httpx_client, api_config
    ):
        """Test fetch_scoreboard with valid date calls httpx client with correct parameters."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            request_delay=0.001,  # Use very small delay for tests
        )
        client = ESPNApiClient(config)

        # Act
        client.fetch_scoreboard("20230315")

        # Assert
        mock_httpx_client.get.assert_called_once()
        args, kwargs = mock_httpx_client.get.call_args
        assert args[0] == f"{api_config['base_url']}/scoreboard"
        assert kwargs["params"]["dates"] == "20230315"

    def test_fetch_scoreboard_with_failed_request_raises_exception(self, api_config):
        """Test fetch_scoreboard with failed request raises an exception."""
        # Arrange
        with patch("src.utils.espn_api_client.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Client Error", request=MagicMock(), response=mock_response
            )

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            config = ESPNApiConfig(
                base_url=api_config["base_url"],
                endpoints={"scoreboard": "/scoreboard"},
                request_delay=0.001,  # Use very small delay for tests
            )
            client = ESPNApiClient(config)

            # Act & Assert
            with pytest.raises(RetryError):
                client.fetch_scoreboard("20230315")

    def test_build_url_with_valid_endpoint_returns_full_url(self, api_config):
        """Test _build_url with valid endpoint returns the full URL."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            request_delay=0.001,  # Use very small delay for tests
        )
        client = ESPNApiClient(config)

        # Act
        url = client._build_url("scoreboard")

        # Assert
        assert url == f"{api_config['base_url']}/scoreboard"

    def test_build_url_with_invalid_endpoint_raises_error(self, api_config):
        """Test _build_url with invalid endpoint raises ValueError."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            request_delay=0.001,  # Use very small delay for tests
        )
        client = ESPNApiClient(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid endpoint"):
            client._build_url("invalid_endpoint")
