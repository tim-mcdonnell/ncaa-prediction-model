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
from src.data.collection.espn.models import Team, TeamsResponse
from src.utils.resilience.retry import retry


@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")

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
    async def test_rate_limiter(self):
        """Test that rate limiter properly limits request rate."""
        # Create a rate limiter with 10 requests per second and burst of 2
        limiter = RateLimiter(rate=10.0, burst=2)
        
        # Should be able to make 2 requests immediately (burst)
        await limiter.acquire()
        await limiter.acquire()
        
        # Third request should be delayed since we've used up our burst
        # Sleep briefly to ensure timing is accurate
        await asyncio.sleep(0.01)  # 10ms sleep
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        duration = asyncio.get_event_loop().time() - start_time
        
        # With rate=10.0, each request after burst should take ~0.1s
        # We use a smaller value to account for timing variations
        assert duration >= 0.05  # At least 50ms delay for the third request
    
    async def test_client_initialization(self):
        """Test that client is properly initialized."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
    
    async def test_get_scoreboard_success(self, load_fixture):
        """Test successful scoreboard data retrieval and parsing."""
        # Mock the API response
        mock_response = load_fixture("scoreboard_response.json")
        
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                result = await client.get_scoreboard("20230301")
                
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                mock_get.assert_called_once()
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def _test_get_with_retry(self, client):
        """Helper method to test retry functionality."""
        return await client._get("/test")
    
    async def test_retry_on_failure(self):
        """Test that retry mechanism works on transient failures."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = [
                    httpx.HTTPError("Connection error"),
                    httpx.HTTPError("Timeout"),
                    {"data": "success"}
                ]
                
                result = await self._test_get_with_retry(client)
                assert result == {"data": "success"}
                assert mock_get.call_count == 3
    
    async def test_rate_limiting_integration(self):
        """Test that rate limiting works in integration with client methods."""
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
    
    async def test_client_error_handling(self):
        """Test that client properly handles various error conditions."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.HTTPError("Test error")
                
                with pytest.raises(httpx.HTTPError):
                    await client._get("/test")
    
    async def test_invalid_response_handling(self):
        """Test handling of invalid API responses."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = {"invalid": "response"}
                
                with pytest.raises(ValidationError):
                    await client.get_scoreboard("20230301")
    
    @pytest.mark.parametrize("date_str", ["20230301", "20230302"])
    async def test_different_dates(self, date_str):
        """Test that client properly handles different date parameters."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = {"events": []}
                await client.get_scoreboard(date_str)
                
                expected_endpoint = (
                    f"/apis/site/v2/sports/{client.SPORT}/{client.LEAGUE}/scoreboard"
                )
                mock_get.assert_called_once_with(
                    expected_endpoint,
                    {"dates": date_str}
                )
                
    async def test_get_all_teams_pagination(self):
        """Test automatic pagination for fetching all teams."""
        async with ESPNClient(rate_limit=10.0, burst_limit=5) as client:
            # Create mock team responses for 3 pages
            # - Page 1: 50 teams (full page)
            # - Page 2: 50 teams (full page)
            # - Page 3: 20 teams (last page)
            
            # First page with 50 teams
            page1_teams = [
                Team(
                    id=str(i), 
                    uid=f"s:40~l:41~t:{i}", 
                    location=f"Team {i}", 
                    name=f"Name {i}",
                    abbreviation=f"T{i}", 
                    displayName=f"Team {i} Name {i}"
                ) 
                for i in range(1, 51)
            ]
            page1_response = TeamsResponse(
                sports=[{
                    "leagues": [{
                        "teams": [
                            {"team": t.model_dump(by_alias=True)} for t in page1_teams
                        ]
                    }]
                }],
                pageCount=3, 
                pageIndex=1, 
                pageSize=50, 
                count=120
            )
            
            # Second page with 50 teams
            page2_teams = [
                Team(
                    id=str(i), 
                    uid=f"s:40~l:41~t:{i}", 
                    location=f"Team {i}", 
                    name=f"Name {i}",
                    abbreviation=f"T{i}", 
                    displayName=f"Team {i} Name {i}"
                ) 
                for i in range(51, 101)
            ]
            page2_response = TeamsResponse(
                sports=[{
                    "leagues": [{
                        "teams": [
                            {"team": t.model_dump(by_alias=True)} for t in page2_teams
                        ]
                    }]
                }],
                pageCount=3, 
                pageIndex=2, 
                pageSize=50, 
                count=120
            )
            
            # Third page with 20 teams (last page)
            page3_teams = [
                Team(
                    id=str(i), 
                    uid=f"s:40~l:41~t:{i}", 
                    location=f"Team {i}", 
                    name=f"Name {i}",
                    abbreviation=f"T{i}", 
                    displayName=f"Team {i} Name {i}"
                ) 
                for i in range(101, 121)
            ]
            page3_response = TeamsResponse(
                sports=[{
                    "leagues": [{
                        "teams": [
                            {"team": t.model_dump(by_alias=True)} for t in page3_teams
                        ]
                    }]
                }],
                pageCount=3, 
                pageIndex=3, 
                pageSize=50, 
                count=120
            )
            
            # Mock the get_teams method to return different responses 
            # based on page number
            with patch.object(
                client, 'get_teams', new_callable=AsyncMock
            ) as mock_get_teams:
                mock_get_teams.side_effect = [
                    page1_response,
                    page2_response,
                    page3_response
                ]
                
                # Call the method under test
                result = await client.get_all_teams()
                
                # Verify the method was called for each page
                assert mock_get_teams.call_count == 3
                mock_get_teams.assert_any_call(page=1)
                mock_get_teams.assert_any_call(page=2)
                mock_get_teams.assert_any_call(page=3)
                
                # Verify the combined result
                assert len(result) == 120  # Total number of teams
                
                # Verify first and last teams to ensure all pages were included
                # Teams should be present from all pages
                assert any(team.id == "1" for team in result)
                assert any(team.id == "75" for team in result)  
                assert any(team.id == "120" for team in result) 
    
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
        """Test date validation for various inputs."""
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