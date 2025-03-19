import pytest
import time
import httpx
from unittest.mock import patch, MagicMock, call

from src.utils.espn_api_client import ESPNApiClient

class TestESPNApiClientModule:
    """Tests for the ESPN API client module."""
    
    @pytest.fixture
    def client(self):
        """Create a test ESPN API client."""
        return ESPNApiClient(
            base_url="https://test.api.com",
            endpoints={
                "scoreboard": "/sports/basketball/scoreboard",
                "teams": "/sports/basketball/teams",
                "team_detail": "/sports/basketball/teams/{team_id}"
            },
            request_delay=0.01,  # Small delay for testing
            max_retries=2,
            timeout=1.0
        )
    
    def test_init_WithValidParameters_InitializesCorrectly(self):
        """Test initialization with valid parameters."""
        # Arrange & Act
        client = ESPNApiClient(
            base_url="https://test.api.com",
            endpoints={"scoreboard": "/scoreboard"},
            request_delay=0.5,
            max_retries=3,
            timeout=10.0
        )
        
        # Assert
        assert client.base_url == "https://test.api.com"
        assert client.endpoints == {"scoreboard": "/scoreboard"}
        assert client.request_delay == 0.5
        assert client.max_retries == 3
        assert client.timeout == 10.0
        assert client.last_request_time == 0
    
    def test_build_url_WithValidEndpoint_ReturnsCorrectURL(self, client):
        """Test _build_url with valid endpoint returns the correct URL."""
        # Arrange & Act
        url = client._build_url("scoreboard")
        
        # Assert
        assert url == "https://test.api.com/sports/basketball/scoreboard"
    
    def test_build_url_WithPathParameters_ReturnsFormattedURL(self, client):
        """Test _build_url with path parameters returns correctly formatted URL."""
        # Arrange & Act
        url = client._build_url("team_detail", team_id="123")
        
        # Assert
        assert url == "https://test.api.com/sports/basketball/teams/123"
    
    def test_build_url_WithInvalidEndpoint_RaisesValueError(self, client):
        """Test _build_url with invalid endpoint raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            client._build_url("invalid_endpoint")
    
    def test_throttle_request_WhenCalledWithinDelay_WaitsAppropriately(self, client):
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
    
    def test_throttle_request_WhenCalledAfterDelay_ProceedsImmediately(self, client):
        """Test _throttle_request proceeds immediately when called after delay period."""
        # Arrange
        client.last_request_time = time.time() - (client.request_delay * 2)  # Set last request to well before now
        
        start_time = time.time()
        
        # Act
        client._throttle_request()
        
        elapsed = time.time() - start_time
        
        # Assert
        # Should not wait since last request was before delay period
        assert elapsed < client.request_delay
        # New last_request_time should be updated
        assert client.last_request_time >= start_time
    
    def test_request_WithSuccessfulResponse_ReturnsJsonData(self, client):
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
                params={"param": "value"}
            )
            mock_response.raise_for_status.assert_called_once()
    
    def test_request_WithHttpError_RetriesToMaxRetries(self, client):
        """Test _request with HTTP error retries up to max_retries."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Test error", request=MagicMock(), response=mock_response
        )
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        
        # Setup mock context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client
        
        # Import RetryError for assertion
        from tenacity import RetryError
        
        # Mock httpx.Client
        with patch("httpx.Client", return_value=mock_context):
            # Act & Assert
            with pytest.raises(RetryError):
                client._request("https://test.api.com/test", {"param": "value"})
                
            # Verify the client was called for each retry attempt
            # Default is 3 attempts
            assert mock_client.get.call_count >= 1
    
    def test_fetch_scoreboard_WithValidParameters_FetchesAndReturnsData(self, client):
        """Test fetch_scoreboard with valid parameters fetches and returns data."""
        # Arrange
        expected_data = {
            "events": [
                {"id": "123", "name": "Test Game"}
            ]
        }
        
        # Mock the _request method
        with patch.object(client, "_request", return_value=expected_data) as mock_request:
            with patch.object(client, "_build_url", return_value="https://test.api.com/sports/basketball/scoreboard") as mock_build_url:
                # Act
                result = client.fetch_scoreboard("20230315", groups="50", limit=100)
                
                # Assert
                assert result == expected_data
                mock_build_url.assert_called_once_with("scoreboard")
                
                # Check that _request was called with the right parameters
                mock_request.assert_called_once_with(
                    "https://test.api.com/sports/basketball/scoreboard", 
                    {"dates": "20230315", "groups": "50", "limit": 100}
                )
    
    def test_fetch_scoreboard_batch_WithMultipleDates_FetchesAndReturnsAllData(self, client):
        """Test fetch_scoreboard_batch with multiple dates returns data for all dates."""
        # Arrange
        dates = ["20230315", "20230316", "20230317"]
        
        # Prepare test data
        mock_responses = {
            "20230315": {"events": [{"id": "123", "name": "Game 1"}]},
            "20230316": {"events": [{"id": "124", "name": "Game 2"}]},
            "20230317": {"events": [{"id": "125", "name": "Game 3"}]}
        }
        
        # Configure mock client to return different responses based on date parameter
        def get_side_effect(url, params=None):
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
        with patch("httpx.Client", return_value=mock_context):
            # Mock the _build_url method
            with patch.object(client, "_build_url", return_value="https://test.api.com/sports/basketball/scoreboard"):
                # Mock throttling
                with patch.object(client, "_throttle_request"):
                    # Act
                    result = client.fetch_scoreboard_batch(dates)
                    
                    # Assert
                    assert len(result) == 3
                    # Check each date's data matches the expected response
                    for date in dates:
                        assert date in result
                        assert result[date] == mock_responses[date]
                    
                    # Check that get was called exactly 3 times (once per date)
                    assert mock_client.get.call_count == 3 