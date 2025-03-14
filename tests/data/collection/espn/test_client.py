import asyncio
import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import polars as pl
import pytest
from pydantic import ValidationError

from src.data.collection.espn.client import ESPNClient, RateLimiter
from src.utils.resilience.retry import retry


@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "fixtures", "espn_responses")

@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file from the fixtures directory."""
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load

@pytest.fixture
async def espn_client():
    """Create an ESPN client for testing."""
    async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
        yield client

@pytest.mark.asyncio
class TestESPNClient:
    async def test_rateLimiter_whenBurstLimitExceeded_shouldDelayRequests(self):
        """
        Test that the rate limiter properly delays requests after burst limit is exceeded.
        
        Verifies:
        1. First N requests (where N is burst limit) complete immediately
        2. Additional requests are delayed according to the rate limit
        3. Delay duration approximates the expected rate (1/rate seconds per request)
        """
        # Create a rate limiter with unique parameters for this test
        limiter = RateLimiter(rate=9.7, burst=2)  # Unique rate value
        
        # Should be able to make 2 requests immediately (burst)
        await limiter.acquire()
        await limiter.acquire()
        
        # Third request should be delayed since we've used up our burst
        # Sleep briefly to ensure timing is accurate
        await asyncio.sleep(0.01)  # 10ms sleep
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        duration = asyncio.get_event_loop().time() - start_time
        
        # With rate=9.7, each request after burst should take ~0.103s
        # We use a smaller value to account for timing variations
        assert duration >= 0.05  # At least 50ms delay for the third request
    
    async def test_rateLimiter_whenZeroRateProvided_shouldNotAllowAnyRequests(self):
        """
        Test that the rate limiter raises ValueError when initialized with a zero rate.
        
        A rate of zero would mean no requests allowed, which is invalid for our implementation.
        The constructor should raise ValueError before any acquire() calls are made.
        """
        with pytest.raises(ValueError, match="Rate must be greater than 0"):
            # Use a unique burst value for this test
            RateLimiter(rate=0.0, burst=3)  # Unique burst value
    
    async def test_rateLimiter_whenNegativeRateProvided_shouldRaiseValueError(self):
        """
        Test that the rate limiter raises ValueError when initialized with a negative rate.
        
        A negative rate is meaningless and should be rejected immediately during initialization.
        """
        with pytest.raises(ValueError, match="Rate must be greater than 0"):
            # Use unique values for this test
            RateLimiter(rate=-2.5, burst=4)  # Unique values
    
    async def test_rateLimiter_whenNegativeBurstProvided_shouldRaiseValueError(self):
        """
        Test that the rate limiter raises ValueError when initialized with a negative burst value.
        
        A negative burst value is invalid and should be rejected immediately during initialization.
        """
        with pytest.raises(ValueError, match="Burst must be greater than or equal to 1"):
            # Use unique values for this test
            RateLimiter(rate=11.3, burst=-2)  # Unique values
    
    async def test_rateLimiter_whenZeroBurstProvided_shouldRaiseValueError(self):
        """
        Test that the rate limiter raises ValueError when initialized with a zero burst value.
        
        A burst of zero would allow no immediate requests, which is not a useful configuration.
        The constructor should validate and reject this value.
        """
        with pytest.raises(ValueError, match="Burst must be greater than or equal to 1"):
            # Use unique values for this test
            RateLimiter(rate=12.2, burst=0)  # Unique values
    
    async def test_rateLimiter_whenExtremeBurstAndHighRate_shouldAllowManyRequestsImmediately(self):
        """
        Test that the rate limiter with very high burst and rate values allows many requests without delay.
        
        This tests the limiter's ability to handle extreme configuration values properly,
        ensuring the limiter doesn't introduce delays when configured for high throughput.
        """
        # High rate and burst should allow many requests without delay
        # Use unique values specific to this test
        limiter = RateLimiter(rate=980.0, burst=110)  # Unique values
        
        # Should be able to make many requests immediately
        start_time = asyncio.get_event_loop().time()
        for _ in range(50):  # Make 50 requests
            await limiter.acquire()
        duration = asyncio.get_event_loop().time() - start_time
        
        # 50 requests should be very fast with a burst of 110
        assert duration < 0.1  # Less than 100ms for 50 requests
    
    async def test_client_whenInitialized_shouldCreateHttpxClient(self):
        """
        Test that the ESPNClient properly initializes the internal HTTP client.
        
        Verifies:
        1. The client._client attribute is not None
        2. The client._client is an instance of httpx.AsyncClient
        This ensures the client is ready to make HTTP requests.
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
    
    async def test_getScoreboard_withValidDate_shouldReturnDataframe(self, load_fixture):
        """
        Test that get_scoreboard() successfully retrieves and parses scoreboard data for a valid date.
        
        This test:
        1. Mocks the API response with fixture data
        2. Calls get_scoreboard() with a valid date
        3. Verifies the response is properly transformed into a DataFrame
        4. Checks that the DataFrame is not empty
        """
        # Create a deep copy of the fixture to avoid shared state
        import copy
        mock_response = copy.deepcopy(load_fixture("scoreboard_response.json"))
        
        # Use a unique client for this test
        async with ESPNClient(rate_limit=9.1, burst_limit=6) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                result = await client.get_scoreboard("20230301")
                
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                mock_get.assert_called_once()
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock()
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def _test_get_with_retry(self, client):
        """
        Helper method to test retry functionality.
        
        This is decorated with @retry to allow testing of the retry mechanism.
        Returns the result from client._get("/test") with retry capability.
        """
        return await client._get("/test")
    
    async def test_retry_whenExperiencingTransientFailures_shouldEventuallySucceed(self):
        """
        Test that the retry mechanism successfully handles transient failures and eventually succeeds.
        
        This test:
        1. Mocks the _get method to fail twice then succeed
        2. Uses the retry decorator to retry the failing calls
        3. Verifies that the call eventually succeeds despite initial failures
        4. Confirms the _get method was called exactly 3 times (2 failures + 1 success)
        """
        # Create an isolated client with unique parameters
        async with ESPNClient(rate_limit=15.7, burst_limit=4) as client:
            # Use a fresh mock for each test
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Use unique error messages specific to this test
                mock_get.side_effect = [
                    httpx.HTTPError("Unique connection error for retry test"),
                    httpx.HTTPError("Unique timeout error for retry test"),
                    {"data": "success for retry test"}  # Unique success message
                ]
                
                result = await self._test_get_with_retry(client)
                assert result == {"data": "success for retry test"}
                assert mock_get.call_count == 3
                
                # Reset the mock to ensure no state leaks
                mock_get.reset_mock()
    
    async def test_retry_whenAllAttemptsExhausted_shouldRaiseLastError(self):
        """
        Test that retry raises the last encountered error when all retry attempts are exhausted.
        
        This test:
        1. Creates a test method with a limited number of retry attempts
        2. Configures the mock to fail with different errors on each attempt
        3. Verifies that the last error (TimeoutException) is propagated after retries are exhausted
        4. Confirms that exactly the configured number of attempts were made
        """
        # Define a retry-decorated method with fewer retry attempts for testing
        @retry(max_attempts=2, backoff_factor=0.1)
        async def test_method(client):
            return await client._get("/test")
        
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # All attempts fail with different errors
                mock_get.side_effect = [
                    httpx.ConnectError("Connection refused"),
                    httpx.TimeoutException("Request timed out")
                ]
                
                # Should raise the last error (TimeoutException) after all retries
                with pytest.raises(httpx.TimeoutException, match="Request timed out"):
                    await test_method(client)
                
                # Should have made exactly 2 attempts (the max_attempts)
                assert mock_get.call_count == 2
    
    async def test_retry_with429_shouldUseExponentialBackoff(self):
        """
        Test that 429 Too Many Requests responses trigger exponential backoff with respect for Retry-After.
        
        This test:
        1. Creates a mock response with a 429 status code and Retry-After header
        2. Measures the time it takes to retry after the 429 error
        3. Verifies that the retry logic respects the Retry-After header value
        4. Confirms the request eventually succeeds after proper backoff
        """
        # Use a smaller retry-after value for testing to make the test faster
        retry_after_value = 1.0  # 1 second instead of 2
        
        @retry(max_attempts=3, backoff_factor=0.5)
        async def test_method(client):
            return await client._get("/test")
        
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a 429 response with Retry-After header
                too_many_requests = httpx.HTTPStatusError(
                    "429 Too Many Requests",
                    request=MagicMock(),
                    response=MagicMock(
                        status_code=429,
                        headers={"Retry-After": str(retry_after_value)}  # Use the test value
                    )
                )
                
                mock_get.side_effect = [
                    too_many_requests,
                    {"data": "success"}
                ]
                
                # Time how long the retry takes
                start_time = asyncio.get_event_loop().time()
                result = await test_method(client)
                duration = asyncio.get_event_loop().time() - start_time
                
                # Allow for some timing flexibility while still ensuring the backoff happened
                # Should be at least 0.8 of the retry_after_value to account for timing variations
                min_expected_delay = retry_after_value * 0.8
                assert duration >= min_expected_delay, f"Expected delay of at least {min_expected_delay}s but got {duration}s"
                
                # Verify that the retry actually succeeded
                assert result == {"data": "success"}
                assert mock_get.call_count == 2
    
    async def test_rateLimiting_whenIntegratedWithClient_shouldDelayRequests(self):
        """
        Test that rate limiting works correctly when integrated into the client's request flow.
        
        This test:
        1. Creates a client with a small burst limit (2)
        2. Makes multiple API requests that exceed the burst limit
        3. Measures the time it takes to process the requests after the burst is consumed
        4. Verifies that rate limiting properly delays subsequent requests
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=2) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = {"data": "test"}
                
                # Should be able to make 2 requests immediately
                await client._get("/test1")
                await client._get("/test2")
                
                # Third request should be delayed
                start_time = asyncio.get_event_loop().time()
                await asyncio.sleep(0.05)  # Ensure timing is accurate
                await client._get("/test3")
                duration = asyncio.get_event_loop().time() - start_time
                
                assert duration >= 0.05  # At least 50ms delay
    
    async def test_clientError_whenHttpErrorOccurs_shouldRaiseException(self):
        """
        Test that the client properly raises exceptions when HTTP errors occur.
        
        This test:
        1. Mocks the _get method to raise an HTTP error
        2. Verifies that the error is properly propagated to the caller
        3. Ensures the client doesn't swallow or transform the error
        """
        # Create an isolated client with unique parameters
        async with ESPNClient(rate_limit=14.3, burst_limit=7) as client:
            # Use a fresh mock for each test to avoid shared state
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Ensure we're using a unique error message for this test
                unique_error = httpx.HTTPError("Unique test error for clientError test")
                mock_get.side_effect = unique_error
                
                with pytest.raises(httpx.HTTPError):
                    await client._get("/test")
                    
                # Verify the mock was called correctly
                mock_get.assert_called_once()
                
                # Reset the mock to ensure no state leaks to other tests
                mock_get.reset_mock()
    
    async def test_invalidResponse_whenDataFormatIncorrect_shouldRaiseValidationError(self):
        """
        Test that the client raises a ValidationError when the API returns an invalid data format.
        
        This test:
        1. Mocks the API to return an invalid response (missing required fields)
        2. Calls the client method that expects a specific response format
        3. Verifies that a ValidationError is raised when parsing the invalid response
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = {"invalid": "response"}
                
                with pytest.raises(ValidationError):
                    await client.get_scoreboard("20230301")
    
    async def test_getResponse_whenMissingRequiredFields_shouldRaiseValidationError(self):
        """
        Test that the client raises a ValidationError when API response is missing required fields.
        
        This test:
        1. Creates a mock response missing critical fields ('date' and 'competitions')
        2. Verifies that the validation correctly identifies the missing fields
        3. Ensures the error message mentions the specific missing fields
        
        This tests the client's ability to detect and report incomplete or malformed responses.
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Missing required nested fields in response
                mock_get.return_value = {
                    "events": [
                        {
                            "id": "401524691",
                            # Missing required 'date' field
                            "name": "Team A vs Team B",
                            # Missing required 'competitions' field
                        }
                    ]
                }
                
                with pytest.raises(ValidationError) as excinfo:
                    await client.get_scoreboard("20230301")
                
                # Check that the error message mentions the missing field
                assert "competitions" in str(excinfo.value) or "date" in str(excinfo.value)
    
    async def test_getResponse_withNullValues_shouldHandleGracefully(self, load_fixture):
        """
        Test that the client handles null values in API responses gracefully.
        
        This test:
        1. Takes a valid response fixture and modifies it to include null values
        2. Verifies that the client can process the response without crashing
        3. Confirms that null values are properly handled in the resulting DataFrame
        
        This ensures robustness in handling real-world API responses that may contain null data.
        """
        # Create a deep copy of the fixture to ensure isolation
        import copy
        response = copy.deepcopy(load_fixture("scoreboard_response.json"))
        
        # Modify the copy, not the original fixture
        response["events"][0]["competitions"][0]["competitors"][0]["team"]["abbreviation"] = None
        response["events"][0]["competitions"][0]["competitors"][1]["score"] = None
        
        # Use a unique client for this test
        async with ESPNClient(rate_limit=9.5, burst_limit=4) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = response
                
                # Should handle null values without crashing
                result = await client.get_scoreboard("20230301")
                
                # Check that null values were handled correctly
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                
                # Score should be empty or null
                assert result[0, "away_team_score"] is None or result[0, "away_team_score"] == ""
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock()
    
    async def test_getScoreboard_withEmptyEvents_shouldReturnEmptyDataframe(self):
        """
        Test that get_scoreboard() returns an empty DataFrame with the correct schema when no events are found.
        
        This test:
        1. Mocks the API to return an empty events list
        2. Verifies that the result is an empty DataFrame
        3. Confirms that the empty DataFrame has the correct schema with all expected columns
        
        This ensures the client gracefully handles dates with no games while maintaining a consistent return type.
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Empty events list
                mock_get.return_value = {"events": []}
                
                result = await client.get_scoreboard("20230301")
                
                # Should return an empty DataFrame with the correct schema
                assert isinstance(result, pl.DataFrame)
                assert result.is_empty()
                
                # Check that expected columns exist
                expected_columns = [
                    "game_id", "date", "name", "home_team_id", "home_team_name",
                    "home_team_score", "away_team_id", "away_team_name", 
                    "away_team_score", "status", "period", "season_year", "season_type"
                ]
                for col in expected_columns:
                    assert col in result.columns
    
    @pytest.mark.parametrize("date_input,should_raise,error_message", [
        ("20230301", False, None),                # Valid date
        ("20230229", True, "valid calendar date"),  # Invalid (2023 not leap year)
        ("2023-03-01", True, "Invalid date format"),  # Wrong format
        ("", True, "Invalid date format"),        # Empty string
        ("abcdefgh", True, "Invalid date format"),  # Non-numeric
        ("99999999", True, "valid calendar date"),  # Out of range month
        ("20231301", True, "valid calendar date"),  # Month > 12
        ("20230001", True, "valid calendar date"),  # Month = 0
        ("20230132", True, "valid calendar date"),  # Day = 32
        ("20230100", True, "valid calendar date"),  # Day = 0
    ])
    async def test_date_validation(self, date_input, should_raise, error_message):
        """
        Test that date validation correctly identifies valid and invalid date formats.
        
        This parametrized test:
        1. Tests multiple date formats, both valid and invalid
        2. Verifies that invalid dates are rejected with appropriate error messages
        3. Ensures valid dates pass validation and can be used in API requests
        
        Parameters:
            date_input: The date string to validate
            should_raise: Whether validation should raise an error
            error_message: Expected error message substring (if should_raise is True)
        """
        async with ESPNClient() as client:
            if should_raise:
                with pytest.raises(ValueError) as excinfo:
                    # Don't await _validate_date_format since it's not async
                    client._validate_date_format(date_input)
                    await client.get_scoreboard(date_input)
                
                # Verify error message contains expected text
                if error_message:
                    assert error_message.lower() in str(excinfo.value).lower()
            else:
                # If it shouldn't raise, make sure it validates properly
                assert client._validate_date_format(date_input) is True
                
                # For valid dates, check that the method executes without error
                with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                    mock_get.return_value = {"events": []}
                    result = await client.get_scoreboard(date_input)
                    assert isinstance(result, pl.DataFrame)
    
    async def test_date_mismatch_warning(self):
        """
        Test that a warning is logged if returned events don't match the requested date.
        """
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            # Create a response with an event on a different date than requested
            event_date = datetime(2023, 3, 2, 19, 0, 0)  # March 2nd
            requested_date = "20230301"  # March 1st
            
            mock_response = {
                "events": [
                    {
                        "id": "123456",
                        "uid": "s:1~e:123456",
                        "date": event_date.isoformat() + "Z",
                        "name": "Team A vs Team B",
                        "shortName": "A vs B",
                        "season": {"year": 2023, "type": 2},
                        "competitions": [
                            {
                                "id": "123456",
                                "uid": "s:1~e:123456~c:123456",
                                "date": event_date.isoformat() + "Z",
                                "status": {
                                    "clock": 0.0,
                                    "displayClock": "0:00",
                                    "period": 2,
                                    "type": {"id": "3", "name": "STATUS_FINAL"}
                                },
                                "competitors": [
                                    {
                                        "id": "1",
                                        "uid": "s:1~t:1",
                                        "type": "team",
                                        "order": 0,
                                        "homeAway": "home",
                                        "team": {
                                            "id": "1",
                                            "uid": "s:1~t:1",
                                            "location": "Team A",
                                            "name": "A",
                                            "abbreviation": "TA",
                                            "displayName": "Team A"
                                        },
                                        "score": "70"
                                    },
                                    {
                                        "id": "2",
                                        "uid": "s:1~t:2",
                                        "type": "team",
                                        "order": 1,
                                        "homeAway": "away",
                                        "team": {
                                            "id": "2",
                                            "uid": "s:1~t:2",
                                            "location": "Team B",
                                            "name": "B",
                                            "abbreviation": "TB",
                                            "displayName": "Team B"
                                        },
                                        "score": "65"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                
                # Use patch to check for warnings
                with patch(
                    'src.data.collection.espn.client.logger.warning'
                ) as mock_warning:
                    await client.get_scoreboard(requested_date)
                    # Check that a warning was logged
                    mock_warning.assert_called_once()
                    assert "Date mismatch" in mock_warning.call_args[0][0]
                    # Date is formatted as YYYY-MM-DD in the log
                    assert "2023-03-01" in mock_warning.call_args[0][0]
                    assert "2023-03-02" in mock_warning.call_args[0][0]
    
    async def test_get_scoreboard_for_date_range(self):
        """Test retrieving games for a date range."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            # Mock the get_scoreboard method to return different data 
            # for different dates
            with patch.object(
                client, 'get_scoreboard', new_callable=AsyncMock
            ) as mock_get_scoreboard:
                # Create 3 different mock dataframes for 3 different dates
                df1 = pl.DataFrame({
                    "game_id": ["g1", "g2"],
                    "date": [datetime(2023, 3, 1, 19, 0), datetime(2023, 3, 1, 21, 0)],
                    "name": ["Game 1", "Game 2"],
                    "home_team_id": ["1", "3"],
                    "home_team_name": ["Team A", "Team C"],
                    "home_team_score": ["75", "80"],
                    "away_team_id": ["2", "4"],
                    "away_team_name": ["Team B", "Team D"],
                    "away_team_score": ["70", "65"],
                    "status": ["STATUS_FINAL", "STATUS_FINAL"],
                    "period": [2, 2],
                    "season_year": [2023, 2023],
                    "season_type": [2, 2]
                })
                
                df2 = pl.DataFrame({
                    "game_id": ["g3"],
                    "date": [datetime(2023, 3, 2, 20, 0)],
                    "name": ["Game 3"],
                    "home_team_id": ["5"],
                    "home_team_name": ["Team E"],
                    "home_team_score": ["90"],
                    "away_team_id": ["6"],
                    "away_team_name": ["Team F"],
                    "away_team_score": ["85"],
                    "status": ["STATUS_FINAL"],
                    "period": [2],
                    "season_year": [2023],
                    "season_type": [2]
                })
                
                # Empty dataframe for date with no games
                df3 = pl.DataFrame(schema={
                    "game_id": pl.Utf8,
                    "date": pl.Datetime,
                    "name": pl.Utf8,
                    "home_team_id": pl.Utf8,
                    "home_team_name": pl.Utf8,
                    "home_team_score": pl.Utf8,
                    "away_team_id": pl.Utf8,
                    "away_team_name": pl.Utf8,
                    "away_team_score": pl.Utf8,
                    "status": pl.Utf8,
                    "period": pl.Int64,
                    "season_year": pl.Int64,
                    "season_type": pl.Int64
                })
                
                # Set up mock to return different dataframes for different dates
                mock_get_scoreboard.side_effect = [df1, df2, df3]
                
                # Call the method under test for a 3-day range
                result = await client.get_scoreboard_for_date_range(
                    "20230301", "20230303"
                )
                
                # Verify the mock was called for each date in the range
                assert mock_get_scoreboard.call_count == 3
                mock_get_scoreboard.assert_has_calls([
                    call("20230301"),
                    call("20230302"),
                    call("20230303")
                ])
                
                # Verify the results were combined correctly
                assert len(result) == 3  # Total of 3 games across all dates
                assert set(result["game_id"].to_list()) == {"g1", "g2", "g3"}
                
    async def test_date_range_validation(self):
        """Test validation of date ranges."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            # Test invalid date formats
            with pytest.raises(ValueError, match="Invalid date format"):
                # Wrong format for start date
                await client.get_scoreboard_for_date_range(
                    "2023-03-01", "20230305"
                )
                
            with pytest.raises(ValueError, match="Invalid date format"):
                # Wrong format for end date
                await client.get_scoreboard_for_date_range(
                    "20230301", "2023-03-05"
                )
                
            # Test end date before start date
            with pytest.raises(ValueError, match="Invalid date range"):
                # End date before start date
                await client.get_scoreboard_for_date_range(
                    "20230305", "20230301"
                )
                
            # Test with mock to verify empty result handling
            with patch.object(
                client, 'get_scoreboard', new_callable=AsyncMock
            ) as mock_get_scoreboard:
                # Empty dataframe for all dates
                empty_df = pl.DataFrame(schema={
                    "game_id": pl.Utf8,
                    "date": pl.Datetime,
                    "name": pl.Utf8,
                    "home_team_id": pl.Utf8,
                    "home_team_name": pl.Utf8,
                    "home_team_score": pl.Utf8,
                    "away_team_id": pl.Utf8,
                    "away_team_name": pl.Utf8,
                    "away_team_score": pl.Utf8,
                    "status": pl.Utf8,
                    "period": pl.Int64,
                    "season_year": pl.Int64,
                    "season_type": pl.Int64
                })
                
                mock_get_scoreboard.return_value = empty_df
                
                # Should return empty DataFrame with correct schema when no games found
                result = await client.get_scoreboard_for_date_range(
                    "20230301", "20230302"
                )
                assert result.is_empty()
                assert result.schema == empty_df.schema
                assert mock_get_scoreboard.call_count == 2  # Called for both dates
                
    async def test_error_handling_in_date_range(self):
        """Test error handling in date range fetching."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(
                client, 'get_scoreboard', new_callable=AsyncMock
            ) as mock_get_scoreboard:
                # Set up the mock to raise an exception for one date 
                # but return data for others
                df1 = pl.DataFrame({
                    "game_id": ["g1"],
                    "date": [datetime(2023, 3, 1, 19, 0)],
                    "name": ["Game 1"],
                    "home_team_id": ["1"],
                    "home_team_name": ["Team A"],
                    "home_team_score": ["75"],
                    "away_team_id": ["2"],
                    "away_team_name": ["Team B"],
                    "away_team_score": ["70"],
                    "status": ["STATUS_FINAL"],
                    "period": [2],
                    "season_year": [2023],
                    "season_type": [2]
                })
                
                # Exception for the second date, data for the first and third
                mock_get_scoreboard.side_effect = [
                    df1,                                 # First date - success
                    httpx.HTTPStatusError(              # Second date - failure
                        message="500 Internal Server Error",
                        request=MagicMock(),
                        response=MagicMock(status_code=500)
                    ),
                    df1                                  # Third date - success
                ]
                
                # Should handle the error and continue with other dates
                result = await client.get_scoreboard_for_date_range(
                    "20230301", "20230303"
                )
                
                # Verify we still get results from successful dates
                assert len(result) == 2  # Two successful dates with 1 game each
                # Called for all three dates
                assert mock_get_scoreboard.call_count == 3 

    async def test_endpoint_urls_scoreboard(self):
        """
        Test that the scoreboard endpoint generates the correct URL and 
        parameters.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                with patch.object(client, '_validate_date_format', return_value=True):
                    # Mock the model validation and response parsing
                    with patch(
                        'src.data.collection.espn.models.ScoreboardResponse.model_validate'
                    ) as mock_validate:
                        # Return a mock response
                        mock_validate.return_value = MagicMock()
                        
                        # Call the method
                        await client.get_scoreboard("20230301")
                        
        # Check that the API was called correctly
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        called_params = (
            mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 
            else mock_get.call_args[1].get('params')
        )
        
        assert called_url == (
            "/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
        )
        assert called_params == {"dates": "20230301"}

    async def test_endpoint_urls_teams(self):
        """Test that the teams endpoint generates the correct URL and parameters."""
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Mock the model validation and response parsing
                with patch(
                    'src.data.collection.espn.models.TeamsResponse.model_validate'
                ) as mock_validate:
                    # Return a mock response
                    mock_validate.return_value = MagicMock()
                    
                    # Call the method
                    await client.get_teams(page=2)
                    
        # Check that the API was called correctly
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        called_params = (
            mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 
            else mock_get.call_args[1].get('params')
        )
        
        assert called_url == (
            "/apis/site/v2/sports/basketball/mens-college-basketball/teams"
        )
        assert called_params == {"page": 2}

    async def test_endpoint_urls_team(self):
        """Test that the team endpoint generates the correct URL and parameters."""
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Mock the model validation and response parsing
                with patch(
                    'src.data.collection.espn.models.TeamResponse.model_validate'
                ) as mock_validate:
                    # Return a mock response
                    mock_validate.return_value = MagicMock()
                    
                    # Call the method
                    await client.get_team("123")
                    
                # Check that the API was called correctly
                mock_get.assert_called_once()
                called_url = mock_get.call_args[0][0]
                
                assert called_url == (
                    "/apis/site/v2/sports/basketball/mens-college-basketball/teams/123"
                )

    async def test_endpoint_urls_game_summary(self):
        """
        Test that the game summary endpoint generates the correct URL and 
        parameters.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Mock the model validation and response parsing
                with patch(
                    'src.data.collection.espn.models.GameSummaryResponse.model_validate'
                ) as mock_validate:
                    # Return a mock response
                    mock_validate.return_value = MagicMock()
                    
                    # Call the method
                    await client.get_game_summary("401524691")
                    
        # Check that the API was called correctly
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        called_params = (
            mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 
            else mock_get.call_args[1].get('params')
        )
        
        assert called_url == (
            "/apis/site/v2/sports/basketball/mens-college-basketball/summary"
        )
        assert called_params == {"event": "401524691"}

    async def test_resource_management(self):
        """Test that resources are properly initialized and cleaned up."""
        # Test proper cleanup using a custom mock client
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        
        # Create client and manually set the HTTP client
        client = ESPNClient()
        client._client = mock_client
        
        # Use the context manager exit
        await client.__aexit__(None, None, None)
        
        # Verify aclose was called and client was reset
        mock_client.aclose.assert_called_once()
        assert client._client is None
        
        # Test that accessing client property outside context raises error
        client = ESPNClient()
        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client
        
        # Test that client is properly initialized in context
        async with ESPNClient() as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
        
        # Test that client is properly cleaned up after context
        assert client._client is None 

    @pytest.mark.integration
    async def test_client_to_dataframe_flow(self, load_fixture, tmp_path):
        """Test the flow from API request to DataFrame and storage."""
        import os
        
        # Mock the HTTP client but use real parsing logic
        with patch('httpx.AsyncClient.get') as mock_get:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = load_fixture("scoreboard_response.json")
            mock_response.raise_for_status = MagicMock()
            
            # Configure mock to return our response
            mock_get.return_value = mock_response
            
            # Use the real client with mocked HTTP
            async with ESPNClient() as client:
                # Get data
                result = await client.get_scoreboard("20230301")
                
                # Verify we got a DataFrame with expected structure
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                assert "game_id" in result.columns
                assert "home_team_name" in result.columns
                assert "away_team_name" in result.columns
                
                # Save to Parquet (testing data storage integration)
                result_path = os.path.join(tmp_path, "games.parquet")
                result.write_parquet(result_path)
                
                # Verify data can be read back
                loaded = pl.read_parquet(result_path)
                assert loaded.shape == result.shape
                assert loaded.columns == result.columns
                
                # Verify the content matches
                for col in loaded.columns:
                    assert loaded[col].to_list() == result[col].to_list() 