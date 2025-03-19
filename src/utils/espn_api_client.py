"""ESPN API client for the NCAA Basketball Prediction Model.

This module provides a client for interacting with the ESPN API for college basketball data,
handling connection throttling, retries, and error handling to ensure reliable data fetching.
"""

import time
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

# Initialize logger
logger = structlog.get_logger(__name__)


class ESPNApiClient:
    """Client for ESPN's undocumented API."""

    def __init__(
        self: "ESPNApiClient",
        base_url: str,
        endpoints: dict[str, str],
        request_delay: float = 1.0,
        max_retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        """Initialize ESPN API client.

        Args:
            base_url: Base URL for the API
            endpoints: Dictionary of endpoint paths
            request_delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.endpoints = endpoints
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.last_request_time = 0.0

        logger.debug(
            "Initialized ESPN API client",
            base_url=base_url,
            endpoints=endpoints,
            request_delay=request_delay,
            max_retries=max_retries,
            timeout=timeout,
        )

    def _build_url(self: "ESPNApiClient", endpoint: str, **kwargs: dict[str, Any]) -> str:
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

        return f"{self.base_url}{path}"

    def get_endpoint_url(self: "ESPNApiClient", endpoint: str, **kwargs: dict[str, Any]) -> str:
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

        if time_since_last < self.request_delay:
            delay = self.request_delay - time_since_last
            logger.debug("Throttling request", delay=delay)
            time.sleep(delay)

        self.last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
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

            # Raise exception for non-200 responses
            response.raise_for_status()

            # Parse JSON response
            return response.json()

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

        data = self._request(url, params)
        logger.debug("Fetched scoreboard data", num_events=len(data.get("events", [])))
        return data

    def fetch_scoreboard_batch(
        self: "ESPNApiClient",
        dates: list[str],
        groups: str = "50",
        limit: int = 200,
    ) -> dict[str, dict[str, Any]]:
        """Fetch scoreboard data for multiple dates concurrently.

        Args:
            dates: List of dates in YYYYMMDD format
            groups: ESPN groups parameter (50 = Division I)
            limit: Maximum number of games to return

        Returns:
            Dictionary mapping dates to their respective JSON responses
        """
        url = self.get_endpoint_url("scoreboard")

        logger.info("Fetching scoreboard data for multiple dates", dates_count=len(dates))

        results: dict[str, dict[str, Any]] = {}

        # Using httpx for concurrent requests
        with httpx.Client(timeout=self.timeout) as client:
            for date in dates:
                # Apply throttling
                self._throttle_request()

                params = {"dates": date, "groups": groups, "limit": limit}

                logger.debug("Making API request", date=date)

                start_time = time.time()
                response = client.get(url, params=params)
                duration = time.time() - start_time

                logger.debug(
                    "API response received",
                    date=date,
                    status_code=response.status_code,
                    duration=duration,
                )

                # Raise exception for non-200 responses
                response.raise_for_status()

                # Parse JSON response
                data = response.json()

                # Log the number of events/games found
                events_count = len(data.get("events", []))
                logger.info("Fetched scoreboard data", date=date, events_count=events_count)

                # Store results
                results[date] = data

        return results
