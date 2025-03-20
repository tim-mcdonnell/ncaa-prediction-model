"""ESPN API client for the NCAA Basketball Prediction Model.

This module provides a client for interacting with the ESPN API for college basketball data,
handling connection throttling, retries, and error handling to ensure reliable data fetching.
Includes asynchronous request capabilities with adaptive backoff.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

# Initialize logger
logger = structlog.get_logger(__name__)

# Constants for HTTP status codes and response thresholds
HTTP_STATUS_OK_MIN = 200
HTTP_STATUS_OK_MAX = 300
HTTP_STATUS_RATE_LIMIT = 429
HTTP_STATUS_CLIENT_ERROR = 400
HTTP_STATUS_SERVER_ERROR = 500
SUSTAINED_SUCCESS_THRESHOLD = 3
MAX_CONCURRENCY_LIMIT = 10


@dataclass
class ESPNApiConfig:
    """Configuration for ESPN API client."""

    # Required parameters
    base_url: str
    endpoints: dict[str, str]

    # Optional parameters with defaults
    initial_request_delay: float = 1.0
    max_retries: int = 3
    timeout: float = 10.0
    max_concurrency: int = 5
    min_request_delay: float = 0.1
    max_request_delay: float = 5.0
    backoff_factor: float = 1.5
    recovery_factor: float = 0.9
    error_threshold: int = 3
    success_threshold: int = 10


class ESPNApiClient:
    """Client for ESPN's undocumented API with asynchronous capabilities and adaptive backoff."""

    def __init__(
        self: "ESPNApiClient",
        config: ESPNApiConfig,
    ) -> None:
        """Initialize ESPN API client.

        Args:
            config: ESPNApiConfig object with client configuration
        """
        self.base_url = config.base_url
        self.endpoints = config.endpoints
        self.current_request_delay = config.initial_request_delay
        self.min_request_delay = config.min_request_delay
        self.max_request_delay = config.max_request_delay
        self.max_retries = config.max_retries
        self.timeout = config.timeout
        self.max_concurrency = config.max_concurrency
        self.backoff_factor = config.backoff_factor
        self.recovery_factor = config.recovery_factor
        self.error_threshold = config.error_threshold
        self.success_threshold = config.success_threshold
        self.last_request_time = 0.0

        # Statistics for adaptive behavior
        self.consecutive_errors = 0
        self.consecutive_successes = 0
        self.concurrent_requests = 0

        # Concurrency control
        self.semaphore = asyncio.Semaphore(self.max_concurrency)

        logger.debug(
            "Initialized ESPN API client",
            base_url=self.base_url,
            endpoints=self.endpoints,
            initial_request_delay=self.current_request_delay,
            min_request_delay=self.min_request_delay,
            max_request_delay=self.max_request_delay,
            max_concurrency=self.max_concurrency,
            backoff_factor=self.backoff_factor,
            recovery_factor=self.recovery_factor,
            max_retries=self.max_retries,
            timeout=self.timeout,
        )

    def _build_url(self: "ESPNApiClient", endpoint: str, **kwargs: str) -> str:
        """Build URL for API endpoint with path parameters.

        Args:
            endpoint: Name of API endpoint
            **kwargs: Path parameters for URL

        Returns:
            Complete URL for API request

        Raises:
            ValueError: If endpoint is not recognized
        """
        if endpoint not in self.endpoints:
            error_msg = f"Invalid endpoint: {endpoint}"
            raise ValueError(error_msg)

        # Build the path
        path = self.endpoints[endpoint]

        # Format path with any provided parameters
        if kwargs:
            path = path.format(**kwargs)

        # Ensure path starts with a slash for proper URL joining
        if not path.startswith("/"):
            path = f"/{path}"

        return f"{self.base_url}{path}"

    def get_endpoint_url(self: "ESPNApiClient", endpoint: str, **kwargs: str) -> str:
        """Get the full URL for an API endpoint.

        Args:
            endpoint: Name of API endpoint
            **kwargs: Path parameters for URL

        Returns:
            Complete URL for API request

        Raises:
            ValueError: If endpoint is not recognized
        """
        return self._build_url(endpoint, **kwargs)

    def _throttle_request(self: "ESPNApiClient") -> None:
        """Apply throttling between requests to avoid rate limiting."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.current_request_delay:
            delay = self.current_request_delay - time_since_last
            logger.debug("Throttling request", delay=delay)
            time.sleep(delay)

        self.last_request_time = time.time()

    async def _throttle_request_async(self: "ESPNApiClient") -> None:
        """Apply asynchronous throttling between requests to avoid rate limiting."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.current_request_delay:
            delay = self.current_request_delay - time_since_last
            logger.debug("Throttling request", delay=delay)
            await asyncio.sleep(delay)

        self.last_request_time = time.time()

    def _track_request_result(
        self: "ESPNApiClient", success: bool, status_code: int | None = None
    ) -> None:
        """Track request results and update adaptive parameters.

        Args:
            success: Whether the request was successful
            status_code: HTTP status code if available
        """
        if success:
            # Reset error counter and increment success counter
            self.consecutive_errors = 0
            self.consecutive_successes += 1

            # Decrease delay after sustained success (but not below minimum)
            if self.consecutive_successes >= SUSTAINED_SUCCESS_THRESHOLD:
                self.current_request_delay = max(
                    self.current_request_delay * self.recovery_factor,
                    self.min_request_delay,
                )
                logger.debug(
                    "Decreased request delay after success",
                    new_delay=self.current_request_delay,
                    consecutive_successes=self.consecutive_successes,
                )

            # Increase concurrency after sustained success
            if self.consecutive_successes >= self.success_threshold:
                self.max_concurrency = min(
                    self.max_concurrency + 1, MAX_CONCURRENCY_LIMIT
                )  # Cap at reasonable maximum
                self.semaphore = asyncio.Semaphore(self.max_concurrency)
                logger.info(
                    "Increased concurrency limit after sustained success",
                    new_concurrency=self.max_concurrency,
                )
                self.consecutive_successes = 0  # Reset counter
        else:
            # Reset success counter and increment error counter
            self.consecutive_successes = 0
            self.consecutive_errors += 1

            # Apply exponential backoff for errors
            self.current_request_delay = min(
                self.current_request_delay * self.backoff_factor,
                self.max_request_delay,
            )

            # Log based on status code
            if status_code:
                if status_code == HTTP_STATUS_RATE_LIMIT:
                    logger.warning(
                        "Rate limit exceeded, increasing delay",
                        new_delay=self.current_request_delay,
                        status_code=status_code,
                    )
                elif status_code >= HTTP_STATUS_SERVER_ERROR:
                    logger.warning(
                        "Server error, increasing delay",
                        new_delay=self.current_request_delay,
                        status_code=status_code,
                    )
                else:
                    logger.warning(
                        "Request error, increasing delay",
                        new_delay=self.current_request_delay,
                        status_code=status_code,
                    )
            else:
                logger.warning(
                    "Request error, increasing delay",
                    new_delay=self.current_request_delay,
                )

            # Decrease concurrency after persistent errors
            if self.consecutive_errors >= self.error_threshold and self.max_concurrency > 1:
                self.max_concurrency -= 1
                self.semaphore = asyncio.Semaphore(self.max_concurrency)
                logger.warning(
                    "Reduced concurrency limit due to persistent errors",
                    new_concurrency=self.max_concurrency,
                )
                self.consecutive_errors = 0  # Reset counter

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))  # type: ignore
    def _request(
        self: "ESPNApiClient",
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the ESPN API with retry logic.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPError: If request fails after retries
        """
        self._throttle_request()

        logger.debug("Making API request", url=url, params=params)

        start_time = time.time()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            duration = time.time() - start_time

            logger.debug(
                "API response received",
                status_code=response.status_code,
                duration=duration,
            )

            # Track result for adaptive backoff
            success = HTTP_STATUS_OK_MIN <= response.status_code < HTTP_STATUS_OK_MAX
            self._track_request_result(success=success, status_code=response.status_code)

            # Raise exception for non-200 responses
            response.raise_for_status()

            # Parse JSON response
            return dict(response.json())

    async def _request_async(
        self: "ESPNApiClient",
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an asynchronous HTTP request to the ESPN API with retry logic.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPError: If request fails after retries
        """
        await self._throttle_request_async()

        logger.debug("Making async API request", url=url, params=params)

        status_code = None
        success = False

        # Acquire semaphore to limit concurrency
        async with self.semaphore:
            self.concurrent_requests += 1
            logger.debug(
                "Acquired semaphore for request",
                concurrent_requests=self.concurrent_requests,
                max_concurrency=self.max_concurrency,
            )

            try:
                start_time = time.time()
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    duration = time.time() - start_time
                    status_code = response.status_code

                    logger.debug(
                        "Async API response received",
                        status_code=status_code,
                        duration=duration,
                    )

                    # Raise exception for non-200 responses
                    response.raise_for_status()

                    # Mark as successful
                    success = True

                    # Parse JSON response - must await the json() coroutine
                    json_data = await response.json()
                    return dict(json_data)
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    "HTTP error during async request",
                    status_code=status_code,
                    url=url,
                )
                raise
            except Exception as e:
                logger.exception(
                    "Unexpected error during async request",
                    error=str(e),
                    url=url,
                )
                raise
            finally:
                self.concurrent_requests -= 1
                # Track result for adaptive backoff
                self._track_request_result(success=success, status_code=status_code)

    async def _retry_request_async(
        self: "ESPNApiClient",
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an asynchronous HTTP request with retries.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        attempts = 0
        last_error: Exception | None = None

        while attempts < self.max_retries:
            try:
                return await self._request_async(url, params)
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors (except 429 - rate limit)
                if (
                    e.response.status_code >= HTTP_STATUS_CLIENT_ERROR
                    and e.response.status_code < HTTP_STATUS_SERVER_ERROR
                    and e.response.status_code != HTTP_STATUS_RATE_LIMIT
                ):
                    raise

                last_error = e
                attempts += 1

                # Exponential backoff before retry
                wait_time = (2**attempts) * 0.5  # 1s, 2s, 4s, ...
                logger.warning(
                    "Request failed, retrying",
                    attempt=attempts,
                    max_retries=self.max_retries,
                    wait_time=wait_time,
                    status_code=e.response.status_code,
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                attempts += 1

                # Exponential backoff before retry
                wait_time = (2**attempts) * 0.5
                logger.warning(
                    "Request failed with error, retrying",
                    attempt=attempts,
                    max_retries=self.max_retries,
                    wait_time=wait_time,
                    error=str(e),
                )
                await asyncio.sleep(wait_time)

        # If we get here, all retries failed
        logger.exception(
            "All retry attempts failed",
            max_retries=self.max_retries,
            url=url,
        )

        if last_error:
            raise last_error
        else:
            # This should never happen, but just in case
            error_msg = f"All {self.max_retries} retry attempts failed for URL: {url}"
            raise RuntimeError(error_msg)

    def fetch_scoreboard(
        self: "ESPNApiClient",
        date: str,
        groups: str = "50",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Fetch scoreboard data for a specific date.

        Args:
            date: Date in YYYYMMDD format
            groups: ESPN groups parameter (50 = Division I)
            limit: Maximum number of games to return

        Returns:
            JSON response as dictionary
        """
        url = self.get_endpoint_url("scoreboard")
        params = {"dates": date, "groups": groups, "limit": limit}

        logger.info("Fetching scoreboard data", date=date, groups=groups, limit=limit)

        data: dict[str, Any] = self._request(url, params)
        logger.debug("Fetched scoreboard data", num_events=len(data.get("events", [])))
        return data

    async def fetch_scoreboard_async(
        self: "ESPNApiClient",
        date: str,
        groups: str = "50",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Asynchronously fetch scoreboard data for a specific date.

        Args:
            date: Date in YYYYMMDD format
            groups: ESPN groups parameter (50 = Division I)
            limit: Maximum number of games to return

        Returns:
            JSON response as dictionary
        """
        url = self.get_endpoint_url("scoreboard")
        params = {"dates": date, "groups": groups, "limit": limit}

        logger.info(
            "Asynchronously fetching scoreboard data", date=date, groups=groups, limit=limit
        )

        data: dict[str, Any] = await self._retry_request_async(url, params)
        logger.debug(
            "Fetched async scoreboard data", num_events=len(data.get("events", [])), date=date
        )
        return data

    def fetch_scoreboard_batch(
        self: "ESPNApiClient",
        dates: list[str],
        groups: str = "50",
        limit: int = 200,
    ) -> dict[str, dict[str, Any]]:
        """Fetch scoreboard data for multiple dates sequentially.

        Note: This method is maintained for backward compatibility.
        New code should use fetch_scoreboard_batch_async for better performance.

        Args:
            dates: List of dates in YYYYMMDD format
            groups: ESPN groups parameter (50 = Division I)
            limit: Maximum number of games to return

        Returns:
            Dictionary mapping dates to their respective JSON responses
        """
        # For backward compatibility, run the async version in a new event loop
        return asyncio.run(self.fetch_scoreboard_batch_async(dates, groups, limit))

    async def fetch_scoreboard_batch_async(
        self: "ESPNApiClient",
        dates: list[str],
        groups: str = "50",
        limit: int = 200,
    ) -> dict[str, dict[str, Any]]:
        """Asynchronously fetch scoreboard data for multiple dates concurrently.

        Args:
            dates: List of dates in YYYYMMDD format
            groups: ESPN groups parameter (50 = Division I)
            limit: Maximum number of games to return

        Returns:
            Dictionary mapping dates to their respective JSON responses
        """
        if not dates:
            return {}

        logger.info(
            "Fetching scoreboard data for multiple dates asynchronously", dates_count=len(dates)
        )

        results: dict[str, dict[str, Any]] = {}
        tasks = []

        async def fetch_single_date(date: str) -> tuple[str, dict[str, Any] | None]:
            """Fetch a single date and return (date, result) tuple."""
            try:
                data = await self.fetch_scoreboard_async(date, groups, limit)
                events_count = len(data.get("events", []))
                logger.info(
                    "Fetched scoreboard data asynchronously", date=date, events_count=events_count
                )
            except Exception as e:
                logger.exception("Failed to fetch scoreboard data", date=date, error=str(e))
                return date, None
            else:
                return date, data

        # Create tasks for all dates
        for date in dates:
            tasks.append(fetch_single_date(date))

        # Gather results
        date_results = await asyncio.gather(*tasks)

        # Process results
        for date, data in date_results:
            if data is not None:
                results[date] = data

        logger.info(
            "Completed fetching scoreboard data",
            success_count=len(results),
            total_dates=len(dates),
        )

        return results
