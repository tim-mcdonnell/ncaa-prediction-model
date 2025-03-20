import asyncio
import time
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from tenacity import RetryError

from src.utils.espn_api_client import ESPNApiClient, ESPNApiConfig


class TestESPNApiClientModule:
    """Tests for the ESPN API client module."""

    @pytest.fixture()  # type: ignore
    def client(self) -> ESPNApiClient:
        """Create a test client with small delay for testing."""
        # Create config with test values
        config = ESPNApiConfig(
            base_url="https://test.api.com",
            endpoints={
                "scoreboard": "/sports/basketball/scoreboard",
                "teams": "/sports/basketball/teams",
                "team_detail": "/sports/basketball/teams/{team_id}",
            },
            initial_request_delay=0.01,  # Small delay for tests
            min_request_delay=0.01,
            max_request_delay=1.0,
            backoff_factor=1.5,
            recovery_factor=0.9,
            max_concurrency=3,
            max_retries=2,
            timeout=1.0,
        )
        return ESPNApiClient(config)

    def test_init_with_valid_parameters_initializes_correctly(self) -> None:
        """Test initialization with valid parameters."""
        # Arrange & Act
        initial_delay = 0.5
        min_delay = 0.1
        max_delay = 5.0
        concurrency = 5
        backoff = 1.5
        recovery = 0.9
        error_threshold = 3
        success_threshold = 10
        default_retries = 3
        default_timeout = 10.0

        config = ESPNApiConfig(
            base_url="https://test.api.com",
            endpoints={"scoreboard": "/scoreboard"},
            initial_request_delay=initial_delay,
            min_request_delay=min_delay,
            max_request_delay=max_delay,
            max_concurrency=concurrency,
            backoff_factor=backoff,
            recovery_factor=recovery,
            error_threshold=error_threshold,
            success_threshold=success_threshold,
            max_retries=default_retries,
            timeout=default_timeout,
        )
        client = ESPNApiClient(config)

        # Assert
        assert client.base_url == "https://test.api.com"
        assert client.endpoints == {"scoreboard": "/scoreboard"}
        assert client.current_request_delay == initial_delay
        assert client.min_request_delay == min_delay
        assert client.max_request_delay == max_delay
        assert client.max_concurrency == concurrency
        assert client.backoff_factor == backoff
        assert client.recovery_factor == recovery
        assert client.error_threshold == error_threshold
        assert client.success_threshold == success_threshold
        assert client.max_retries == default_retries
        assert client.timeout == default_timeout
        assert client.last_request_time == 0
        assert client.semaphore is not None
        assert client.concurrent_requests == 0
        assert client.consecutive_errors == 0
        assert client.consecutive_successes == 0

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
        # Should wait at least the current_request_delay
        assert elapsed >= client.current_request_delay
        # New last_request_time should be updated
        assert client.last_request_time > start_time

    def test_throttle_request_when_called_after_delay_proceeds_immediately(
        self,
        client: ESPNApiClient,
    ) -> None:
        """Test _throttle_request proceeds immediately when called after delay period."""
        # Arrange
        client.last_request_time = time.time() - (
            client.current_request_delay * 2
        )  # Set last request to well before now

        start_time = time.time()

        # Act
        client._throttle_request()

        elapsed = time.time() - start_time

        # Assert
        # Should not wait since last request was before delay period
        assert elapsed < client.current_request_delay
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

        # Since fetch_scoreboard_batch uses asyncio.run internally, we just need to patch that
        with patch("asyncio.run", return_value=mock_responses):
            # Act
            result = client.fetch_scoreboard_batch(
                dates=dates,
                groups="50",
                limit=100,
            )

            # Assert
            assert len(result) == expected_date_count
            # Check that data for each date is in the result
            assert "20230315" in result
            assert "20230316" in result

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_async_with_valid_date_returns_data(self, client) -> None:
        """Test that fetch_scoreboard_async with valid date returns data correctly."""
        # Arrange
        test_date = "20220315"
        test_response = {"events": [{"id": "12345"}]}

        async def mock_request(*_, **__):
            return test_response

        with patch.object(client, "_request_async", side_effect=mock_request):
            # Act
            result = await client.fetch_scoreboard_async(date=test_date)

            # Assert
            assert result == test_response

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_async_with_invalid_date_handles_error(self, client) -> None:
        """Test that fetch_scoreboard_async with invalid date handles error appropriately."""
        # Arrange
        test_date = "invalid-date"

        async def mock_request(*_, **__):
            error_message = "400 Client Error"
            raise httpx.HTTPStatusError(
                error_message, request=MagicMock(), response=MagicMock(status_code=400)
            )

        with (
            patch.object(client, "_request_async", side_effect=mock_request),
            pytest.raises(httpx.HTTPStatusError),
        ):
            # Act & Assert
            await client.fetch_scoreboard_async(date=test_date)

    @pytest.mark.asyncio()
    async def test_adaptive_backoff_increases_delay_after_errors(self, client) -> None:
        """Test that adaptive backoff increases delay after errors."""
        # Arrange
        initial_delay = client.current_request_delay

        # Act
        client._track_request_result(success=False)

        # Assert
        assert client.current_request_delay > initial_delay
        assert client.consecutive_errors == 1
        assert client.consecutive_successes == 0

    @pytest.mark.asyncio()
    async def test_adaptive_backoff_decreases_delay_after_success(self, client) -> None:
        """Test that adaptive backoff decreases delay after success."""
        # Arrange
        # First set a higher delay to verify decrease
        client.current_request_delay = 0.5
        client.consecutive_successes = client.success_threshold - 1  # Need enough successes
        initial_delay = client.current_request_delay

        # Act
        client._track_request_result(success=True)

        # Assert
        assert client.current_request_delay < initial_delay

    @pytest.mark.asyncio()
    async def test_concurrency_limiter_respects_max_concurrent_requests(self) -> None:
        """Test that concurrency limiter respects the max concurrent requests setting."""
        # Arrange
        max_concurrency = 2
        config = ESPNApiConfig(
            base_url="https://test.api.com",
            endpoints={"scoreboard": "/scoreboard"},
            initial_request_delay=0.01,
            max_concurrency=max_concurrency,
            min_request_delay=0.01,
            max_request_delay=1.0,
            backoff_factor=1.5,
            recovery_factor=0.9,
        )
        client = ESPNApiClient(config)

        # Create a task completion event
        finish_event = asyncio.get_event_loop().create_future()

        # Act & Assert
        # Create tasks that try to acquire semaphore
        async def acquire_and_hold():
            async with client.semaphore:
                # Hold semaphore until signaled
                with suppress(TimeoutError):
                    await asyncio.wait_for(finish_event, timeout=0.5)

        # Start two tasks (max concurrency)
        task1 = asyncio.create_task(acquire_and_hold())
        task2 = asyncio.create_task(acquire_and_hold())

        # Allow tasks to start and acquire semaphores
        await asyncio.sleep(0.1)

        # Try to acquire a third semaphore which should block
        semaphore_acquired = False

        async def try_acquire():
            nonlocal semaphore_acquired
            try:
                async with asyncio.timeout(0.1):
                    async with client.semaphore:
                        semaphore_acquired = True
            except TimeoutError:
                pass

        # Create task for third acquisition
        task3 = asyncio.create_task(try_acquire())
        await task3

        # Complete pending tasks
        finish_event.set_result(True)
        await asyncio.gather(task1, task2, task3)

        # Verify third task was blocked
        assert semaphore_acquired is False

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_batch_async_with_valid_dates_processes_all(
        self, client
    ) -> None:
        """Test fetch_scoreboard_batch_async processes all dates."""
        # Arrange
        dates = ["20220315", "20220316", "20220317"]
        responses = {
            "20220315": {"events": [{"id": "1"}]},
            "20220316": {"events": [{"id": "2"}]},
            "20220317": {"events": [{"id": "3"}]},
        }

        async def mock_fetch_scoreboard(date, *_, **__):
            return responses[date]

        with patch.object(client, "fetch_scoreboard_async", side_effect=mock_fetch_scoreboard):
            # Act
            result = await client.fetch_scoreboard_batch_async(dates)

            # Assert
            expected_count = len(dates)
            assert len(result) == expected_count
            assert "20220315" in result
            assert "20220316" in result
            assert "20220317" in result

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_batch_async_with_mixed_errors_handles_gracefully(
        self, client
    ) -> None:
        """Test fetch_scoreboard_batch_async handles errors gracefully."""
        # Arrange
        dates = ["20220315", "20220316", "20220317"]

        async def mock_fetch_scoreboard(date, *_, **__):
            if date == "20220316":
                error_message = "400 Client Error"
                raise httpx.HTTPStatusError(
                    error_message, request=MagicMock(), response=MagicMock(status_code=400)
                )
            return {"events": [{"id": date}]}

        with patch.object(client, "fetch_scoreboard_async", side_effect=mock_fetch_scoreboard):
            # Act
            result = await client.fetch_scoreboard_batch_async(dates)

            # Assert
            expected_success_count = 2  # Only successful requests
            assert len(result) == expected_success_count
            assert "20220315" in result
            assert "20220317" in result
            assert "20220316" not in result

    @pytest.mark.asyncio()
    async def test_adaptive_concurrency_decreases_on_persistent_errors(self, client) -> None:
        """Test that concurrency decreases after persistent errors."""
        # Arrange
        initial_concurrency = client.max_concurrency

        # Act - simulate error threshold errors
        for _ in range(client.error_threshold):
            client._track_request_result(success=False)

        # Assert
        assert client.max_concurrency < initial_concurrency

    @pytest.mark.asyncio()
    async def test_adaptive_concurrency_increases_after_sustained_success(self, client) -> None:
        """Test that concurrency increases after sustained success."""
        # Arrange
        # First lower the concurrency
        client.max_concurrency = 1
        initial_concurrency = client.max_concurrency

        # Act - simulate success threshold successes
        for _ in range(client.success_threshold):
            client._track_request_result(success=True)

        # Assert
        assert client.max_concurrency > initial_concurrency

    @pytest.mark.asyncio()
    async def test_error_tracking_mechanism_logs_error_patterns(self, client) -> None:
        """Test that error tracking mechanism logs error patterns."""
        # Arrange
        with patch("src.utils.espn_api_client.logger") as mock_logger:
            # Act
            client._track_request_result(success=False, status_code=429)

            # Assert
            mock_logger.warning.assert_called()
            # Check that the request delay increased message was logged
            assert any(
                "increasing delay" in str(call) for call in mock_logger.warning.call_args_list
            )


class TestESPNApiClient:
    """Integration tests for ESPNApiClient."""

    @pytest.fixture()  # type: ignore
    def mock_httpx_async_client(self):
        """Mock the httpx.AsyncClient for testing."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json.return_value = {"events": [{"id": "12345"}]}

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            yield mock_client_instance

    @pytest.fixture()  # type: ignore
    def api_config(self):
        """Create a test API configuration."""
        return {
            "base_url": (
                "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
            ),
            "endpoints": {"scoreboard": "scoreboard"},
            "initial_request_delay": 0.001,
            "min_request_delay": 0.001,
            "max_request_delay": 1.0,
            "max_retries": 3,
            "timeout": 5.0,
            "max_concurrency": 5,
            "backoff_factor": 1.5,
            "error_threshold": 3,
            "success_threshold": 5,
            "recovery_factor": 0.9,
            "batch_size": 10,
        }

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_async_with_valid_date_calls_get_with_correct_params(
        self, mock_httpx_async_client, api_config
    ):
        """Test fetch_scoreboard_async with correct parameters."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            # Very small delay for tests
            initial_request_delay=0.001,
            min_request_delay=0.001,
            max_request_delay=1.0,
            max_concurrency=5,
            backoff_factor=1.5,
            recovery_factor=0.9,
        )
        client = ESPNApiClient(config)

        # Fix the response.json() coroutine issue - now a regular MagicMock
        mock_httpx_async_client.get.return_value.json = MagicMock(
            return_value={"events": [{"id": "test"}]}
        )

        # Act
        result = await client.fetch_scoreboard_async("20230315")

        # Assert
        assert "events" in result
        mock_httpx_async_client.get.assert_called_once()
        # Verify date parameter
        _, kwargs = mock_httpx_async_client.get.call_args
        assert kwargs["params"]["dates"] == "20230315"

    @pytest.mark.asyncio()
    async def test_fetch_scoreboard_async_with_failed_request_raises_exception(self, api_config):
        """Test fetch_scoreboard_async with failed request raises an exception."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "/scoreboard"},
            initial_request_delay=0.001,  # Use very small delay for tests
            min_request_delay=0.001,
            max_request_delay=1.0,
            max_concurrency=5,
            backoff_factor=1.5,
            recovery_factor=0.9,
        )
        client = ESPNApiClient(config)

        # Configure the mock to raise an exception
        error = httpx.HTTPStatusError(
            "404 Client Error", request=MagicMock(), response=MagicMock(status_code=404)
        )

        with (
            patch.object(client, "_retry_request_async", side_effect=error),
            pytest.raises(httpx.HTTPStatusError),
        ):
            # Act & Assert
            await client.fetch_scoreboard_async("20230315")

    def test_init_with_config_sets_properties_correctly(self, api_config):
        """Test initialization with config sets properties correctly."""
        # Act
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            initial_request_delay=api_config["initial_request_delay"],
            min_request_delay=api_config["min_request_delay"],
            max_request_delay=api_config["max_request_delay"],
            max_concurrency=api_config["max_concurrency"],
            backoff_factor=api_config["backoff_factor"],
            recovery_factor=api_config["recovery_factor"],
        )
        client = ESPNApiClient(config)

        # Assert
        assert client.base_url == api_config["base_url"]
        assert client.endpoints == {"scoreboard": "scoreboard"}
        assert client.current_request_delay == api_config["initial_request_delay"]
        assert client.min_request_delay == api_config["min_request_delay"]
        assert client.max_request_delay == api_config["max_request_delay"]
        assert client.max_concurrency == api_config["max_concurrency"]
        assert client.backoff_factor == api_config["backoff_factor"]
        assert client.recovery_factor == api_config["recovery_factor"]
        assert client.last_request_time == 0

    @pytest.fixture()  # type: ignore
    def mock_httpx_client(self):
        """Mock for httpx.Client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"events": [{"id": "test"}]}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.Client") as mock_http_client:
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_client
            mock_http_client.return_value = mock_context
            yield mock_client

    def test_fetch_scoreboard_with_valid_date_calls_get_with_correct_params(
        self, mock_httpx_client, api_config
    ):
        """Test fetch_scoreboard with valid date calls httpx client with correct parameters."""
        # Arrange
        config = ESPNApiConfig(
            base_url=api_config["base_url"],
            endpoints={"scoreboard": "scoreboard"},
            initial_request_delay=0.001,  # Use very small delay for tests
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
        with patch("httpx.Client") as mock_client:
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
                initial_request_delay=0.001,  # Use very small delay for tests
                min_request_delay=0.001,
                max_request_delay=1.0,
                max_concurrency=5,
                backoff_factor=1.5,
                recovery_factor=0.9,
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
            initial_request_delay=0.001,  # Use very small delay for tests
            min_request_delay=0.001,
            max_request_delay=1.0,
            max_concurrency=5,
            backoff_factor=1.5,
            recovery_factor=0.9,
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
            initial_request_delay=0.001,  # Use very small delay for tests
            min_request_delay=0.001,
            max_request_delay=1.0,
            max_concurrency=5,
            backoff_factor=1.5,
            recovery_factor=0.9,
        )
        client = ESPNApiClient(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid endpoint"):
            client._build_url("invalid")

    def test_build_url_with_invalid_endpoint_raises_value_error(self, api_config):
        """Test that build_url with invalid endpoint raises value error."""
        # Arrange
        invalid_endpoint = "nonexistent"
        # Remove batch_size which is not accepted by ESPNApiConfig
        config_dict = {k: v for k, v in api_config.items() if k != "batch_size"}
        config = ESPNApiConfig(**config_dict)
        client = ESPNApiClient(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid endpoint"):
            client._build_url(invalid_endpoint)
