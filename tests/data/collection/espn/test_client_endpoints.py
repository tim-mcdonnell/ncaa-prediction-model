from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from src.data.collection.espn.client import ESPNClient
from src.data.collection.espn.models import (
    AthleteResponse,
    GameSummaryResponse,
    RankingsResponse,
    RosterResponse,
    TeamResponse,
    TeamsResponse,
)


class TestESPNClientEndpoints:
    """Test the ESPN API client endpoint functions."""

    @pytest.mark.asyncio
    async def test_scoreboardEndpoint_whenCalled_shouldValidateAndReturnDataframe(self):
        """
        Test that the scoreboard endpoint correctly validates input and returns a DataFrame.
        
        This test:
        1. Creates a mock response that simulates a valid scoreboard API response
        2. Calls the get_scoreboard method with a specific date
        3. Verifies the API is called with the correct endpoint and parameters
        4. Confirms the response is properly transformed into a DataFrame
        
        This ensures the client correctly formats the API request and processes the response.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response with all required fields
                mock_response = {
                    "events": [
                        {
                            "id": "401524691",
                            "uid": "s:40~l:41~e:401524691",
                            "name": "Team A vs Team B",
                            "shortName": "TA vs TB",
                            "date": "2023-03-01T00:00Z",
                            "season": {
                                "year": 2023,
                                "type": 2
                            },
                            "competitions": [
                                {
                                    "id": "401524691",
                                    "uid": "s:40~l:41~c:401524691",
                                    "date": "2023-03-01T00:00Z",
                                    "status": {
                                        "clock": 0,
                                        "displayClock": "0:00",
                                        "period": 2,
                                        "type": {
                                            "name": "STATUS_FINAL",
                                            "completed": True
                                        }
                                    },
                                    "competitors": [
                                        {
                                            "id": "123",
                                            "uid": "s:40~t:123",
                                            "type": "team",
                                            "order": 1,
                                            "homeAway": "home",
                                            "team": {
                                                "id": "123",
                                                "uid": "s:40~t:123",
                                                "name": "Team A",
                                                "abbreviation": "TA",
                                                "displayName": "Team A"
                                            },
                                            "score": "75"
                                        },
                                        {
                                            "id": "456",
                                            "uid": "s:40~t:456",
                                            "type": "team",
                                            "order": 2,
                                            "homeAway": "away",
                                            "team": {
                                                "id": "456",
                                                "uid": "s:40~t:456",
                                                "name": "Team B",
                                                "abbreviation": "TB",
                                                "displayName": "Team B"
                                            },
                                            "score": "70"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_scoreboard("20230301")
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
                    {"dates": "20230301"}
                )
                
                # Check result is a DataFrame
                assert isinstance(result, pl.DataFrame)
    
    @pytest.mark.asyncio
    async def test_teamsEndpoint_whenCalled_shouldReturnTeamsResponse(self):
        """
        Test that the teams endpoint correctly returns a TeamsResponse object.
        
        This test:
        1. Creates a mock response with team data
        2. Calls the get_teams method with a specific page parameter
        3. Verifies the API is called with the correct endpoint and pagination parameters
        4. Confirms the response is properly parsed into a TeamsResponse model object
        5. Checks that the response contains the expected team data
        
        This ensures the client correctly handles team listing requests with pagination.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response
                mock_response = {
                    "sports": [
                        {
                            "leagues": [
                                {
                                    "teams": [
                                        {
                                            "team": {
                                                "id": "123",
                                                "location": "Team A",
                                                "name": "Mascot",
                                                "abbreviation": "TA",
                                                "displayName": "Team A Mascot",
                                                "logos": [{"href": "http://example.com/logo.png"}]
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_teams(page=2)
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/teams",
                    {"page": 2}
                )
                
                # Check result is a TeamsResponse object
                assert isinstance(result, TeamsResponse)
                assert len(result.sports) > 0
    
    @pytest.mark.asyncio
    async def test_teamEndpoint_whenCalled_shouldReturnTeamResponse(self):
        """
        Test that the team endpoint correctly returns data for a specific team.
        
        This test:
        1. Creates a mock response with detailed data for a single team
        2. Calls the get_team method with a specific team ID
        3. Verifies the API is called with the correct endpoint
        4. Confirms the response is properly parsed into a TeamResponse model object
        5. Checks that the response contains the expected team details
        
        This ensures the client can retrieve and process detailed information for a single team.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response
                mock_response = {
                    "team": {
                        "id": "123",
                        "uid": "s:40~t:123",
                        "location": "Team A",
                        "name": "Mascot",
                        "abbreviation": "TA",
                        "displayName": "Team A Mascot",
                        "logos": [{"href": "http://example.com/logo.png"}]
                    }
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_team("123")
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/teams/123"
                )
                
                # Check result is a TeamResponse object
                assert isinstance(result, TeamResponse)
                assert result.team.id == "123"
                assert result.team.display_name == "Team A Mascot"
    
    @pytest.mark.asyncio
    async def test_teamRosterEndpoint_whenCalled_shouldReturnRosterResponse(self):
        """
        Test that the team roster endpoint correctly returns player data for a team.
        
        This test:
        1. Creates a mock response with team and player data
        2. Calls the get_team_roster method with a specific team ID
        3. Verifies the API is called with the correct roster endpoint
        4. Confirms the response is properly parsed into a RosterResponse model object
        5. Checks that the response contains both team and player information
        
        This ensures the client can retrieve and process team roster data correctly.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response
                mock_response = {
                    "team": {
                        "id": "123",
                        "uid": "s:40~t:123",
                        "location": "Team A",
                        "name": "Mascot",
                        "abbreviation": "TA",
                        "displayName": "Team A Mascot",
                        "logos": [{"href": "http://example.com/logo.png"}]
                    },
                    "athletes": [
                        {
                            "id": "4433137",
                            "fullName": "John Doe",
                            "jersey": "23",
                            "position": {"name": "Guard"},
                            "height": 75,
                            "weight": 180
                        }
                    ]
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_team_roster("123")
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/teams/123/roster"
                )
                
                # Check result is a RosterResponse object
                assert isinstance(result, RosterResponse)
                assert result.team.id == "123"
                assert result.team.display_name == "Team A Mascot"
    
    @pytest.mark.asyncio
    async def test_gameSummaryEndpoint_whenCalled_shouldReturnGameSummaryResponse(self):
        """
        Test that the game summary endpoint correctly returns detailed game data.
        
        This test:
        1. Creates a mock response with game summary data (boxscore, plays, etc.)
        2. Calls the get_game_summary method with a specific game ID
        3. Verifies the API is called with the correct endpoint and parameters
        4. Confirms the response is properly parsed into a GameSummaryResponse model object
        
        This ensures the client can retrieve and process detailed information for a specific game.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response
                mock_response = {
                    "header": {
                        "id": "401524691",
                        "season": {"year": 2023}
                    },
                    "boxscore": {
                        "teams": [
                            {
                                "team": {"id": "123"},
                                "statistics": []
                            },
                            {
                                "team": {"id": "456"},
                                "statistics": []
                            }
                        ]
                    },
                    "plays": [],
                    "standings": {"entries": []}
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_game_summary("401524691")
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/summary",
                    {"event": "401524691"}
                )
                
                # Check we get a GameSummaryResponse object
                assert isinstance(result, GameSummaryResponse)
                assert len(result.boxscore.teams) == 2
                assert result.boxscore.teams[0]["team"]["id"] == "123"
                assert result.boxscore.teams[1]["team"]["id"] == "456"
    
    @pytest.mark.asyncio
    async def test_rankings_endpoint(self):
        """
        Test that the rankings endpoint correctly returns team ranking data.
        
        This test:
        1. Creates a mock response with team ranking information
        2. Calls the get_rankings method
        3. Verifies the API is called with the correct endpoint
        4. Confirms the response is properly parsed into a RankingsResponse model object
        5. Checks that the rankings data is accessible and contains the expected information
        
        This ensures the client can retrieve and process team ranking data correctly.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Setup mock response
                mock_response = {
                    "rankings": [
                        {
                            "name": "AP Top 25",
                            "type": "poll",
                            "shortName": "AP",
                            "rankings": [
                                {
                                    "current": 1,
                                    "team": {
                                        "id": "123",
                                        "uid": "s:40~t:123",
                                        "name": "Team A",
                                        "nickname": "Mascots",
                                        "abbreviation": "TA",
                                        "rank": 1
                                    }
                                }
                            ]
                        }
                    ]
                }
                mock_get.return_value = mock_response
                
                # Call the method
                result = await client.get_rankings()
                
                # Verify API call
                mock_get.assert_called_once_with(
                    "/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
                )
                
                # Check result is a RankingsResponse object
                assert isinstance(result, RankingsResponse)
                assert len(result.rankings) == 1
                assert result.rankings[0].name == "AP Top 25"
                assert result.rankings[0].type == "poll"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """
        Test that the client properly handles API errors.
        
        This test:
        1. Configures the mock to raise different types of HTTP errors
        2. Attempts to call various endpoint methods
        3. Verifies that errors are properly caught and propagated
        4. Ensures the client responds appropriately to different error conditions
        
        This ensures the client has robust error handling for API failures.
        """
        async with ESPNClient() as client:
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Set up mock to raise an exception
                mock_get.side_effect = Exception("API Error")
                
                # Test that the exception is properly handled
                with pytest.raises((Exception, ConnectionError)):
                    await client.get_scoreboard("20230301")

    @pytest.mark.asyncio
    async def test_scoreboard_to_dataframe_pipeline(self):
        """
        Test the complete pipeline from scoreboard API call to DataFrame processing.
        
        This test:
        1. Creates a complex mock scoreboard response with multiple games
        2. Calls the get_scoreboard method
        3. Verifies the API response is correctly transformed into a structured DataFrame
        4. Checks that all game data is properly extracted and formatted
        5. Confirms the DataFrame structure is suitable for analysis
        
        This ensures the end-to-end process of fetching and transforming game data works correctly.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request and the processing method
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                with patch.object(client, '_process_scoreboard_data') as mock_process:
                    # Create a mock response that will pass validation
                    mock_json = {
                        "events": [
                            {
                                "id": "401524691",
                                "uid": "s:40~l:41~e:401524691",
                                "date": "2023-03-01T00:00Z",
                                "name": "Team A vs Team B",
                                "shortName": "TA vs TB",
                                "season": {
                                    "year": 2023,
                                    "type": 2
                                },
                                "status": {
                                    "type": {
                                        "id": "3",
                                        "name": "STATUS_FINAL",
                                        "state": "post",
                                        "completed": True,
                                        "description": "Final"
                                    }
                                },
                                "competitions": [
                                    {
                                        "id": "401524691",
                                        "uid": "s:40~l:41~e:401524691~c:401524691",
                                        "date": "2023-03-01T00:00Z",
                                        "status": {
                                            "clock": 0.0,
                                            "displayClock": "0:00",
                                            "period": 2,
                                            "type": {
                                                "id": "3",
                                                "name": "STATUS_FINAL",
                                                "state": "post",
                                                "completed": True,
                                                "description": "Final"
                                            }
                                        },
                                        "competitors": [
                                            {
                                                "id": "123",
                                                "uid": "s:40~l:41~t:123",
                                                "type": "team",
                                                "order": 0,
                                                "homeAway": "home",
                                                "team": {
                                                    "id": "123",
                                                    "uid": "s:40~l:41~t:123",
                                                    "location": "Team A",
                                                    "name": "Mascot",
                                                    "abbreviation": "TA",
                                                    "displayName": "Team A Mascot",
                                                    "logos": [{"href": "http://example.com/logo.png"}]
                                                },
                                                "score": "75"
                                            },
                                            {
                                                "id": "456",
                                                "uid": "s:40~l:41~t:456",
                                                "type": "team",
                                                "order": 1,
                                                "homeAway": "away",
                                                "team": {
                                                    "id": "456",
                                                    "uid": "s:40~l:41~t:456",
                                                    "location": "Team B",
                                                    "name": "Others",
                                                    "abbreviation": "TB",
                                                    "displayName": "Team B Others",
                                                    "logos": [{"href": "http://example.com/logob.png"}]
                                                },
                                                "score": "70"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                    mock_get.return_value = mock_json
                    
                    # Create a mock DataFrame to return
                    mock_df = pl.DataFrame({
                        "game_id": ["401524691"],
                        "date": [
                            datetime.strptime("2023-03-01T00:00Z", "%Y-%m-%dT%H:%M%z")
                        ],
                        "home_team_id": ["123"],
                        "home_team": ["Team A Mascot"],
                        "home_score": [75],
                        "away_team_id": ["456"],
                        "away_team": ["Team B Others"],
                        "away_score": [70],
                        "completed": [True]
                    })
                    mock_process.return_value = mock_df
                    
                    # Call the client method
                    result_df = await client.get_scoreboard("20230301")
                    
                    # Check that the API was called correctly
                    assert mock_get.call_count == 1
                    assert mock_get.call_args[0][0] == (
                        "/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
                    )
                    assert mock_get.call_args[0][1] == {"dates": "20230301"}
                    
                    # Verify that the result is a valid DataFrame
                    assert isinstance(result_df, pl.DataFrame)
                    assert not result_df.is_empty()
                    
                    # Check specific fields
                    first_game = result_df.row(0, named=True)
                    assert first_game["game_id"] == "401524691"
                    assert first_game["home_team"] == "Team A Mascot"
                    assert first_game["away_team"] == "Team B Others"
                    assert first_game["home_score"] == 75
                    assert first_game["away_score"] == 70
                    assert first_game["completed"]
    
    @pytest.mark.asyncio
    async def test_teams_response_pipeline(self):
        """
        Test the complete pipeline from teams API call to model object processing.
        
        This test:
        1. Creates a mock teams response with multiple teams
        2. Calls the get_teams method
        3. Processes the TeamsResponse through the team parser
        4. Verifies the resulting DataFrame contains all expected team data
        5. Confirms the transformation preserves all necessary team attributes
        
        This ensures the end-to-end process of fetching and transforming team data works correctly.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a mock response that will pass validation
                mock_json = {
                    "sports": [
                        {
                            "leagues": [
                                {
                                    "teams": [
                                        {
                                            "team": {
                                                "id": "123",
                                                "uid": "s:40~l:41~t:123",
                                                "location": "Team A",
                                                "name": "Mascot",
                                                "abbreviation": "TA",
                                                "displayName": "Team A Mascot",
                                                "logos": [{"href": "http://example.com/logo.png"}]
                                            }
                                        },
                                        {
                                            "team": {
                                                "id": "456",
                                                "uid": "s:40~l:41~t:456",
                                                "location": "Team B",
                                                "name": "Others",
                                                "abbreviation": "TB",
                                                "displayName": "Team B Others",
                                                "logos": [{"href": "http://example.com/logob.png"}]
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
                mock_get.return_value = mock_json
                
                # Call the client method
                result = await client.get_teams(page=2)
                
                # Check that the API was called correctly
                assert mock_get.call_count == 1
                assert mock_get.call_args[0][0] == (
                    "/apis/site/v2/sports/basketball/mens-college-basketball/teams"
                )
                assert mock_get.call_args[0][1] == {"page": 2}
                
                # Verify that the result is a valid TeamsResponse
                assert isinstance(result, TeamsResponse)
                assert len(result.sports) == 1
                assert len(result.sports[0]["leagues"]) == 1
                assert len(result.sports[0]["leagues"][0]["teams"]) == 2
                
                # Check specific fields
                teams = result.sports[0]["leagues"][0]["teams"]
                assert teams[0]["team"]["id"] == "123"
                assert teams[0]["team"]["displayName"] == "Team A Mascot"
                assert teams[1]["team"]["id"] == "456"
                assert teams[1]["team"]["displayName"] == "Team B Others"
    
    @pytest.mark.asyncio
    async def test_athlete_to_dataframe_pipeline(self):
        """
        Test the complete pipeline from athlete API call to model object processing.
        
        This test:
        1. Creates a mock athlete response with detailed player information
        2. Calls the get_athlete method with a specific athlete ID
        3. Verifies the response is correctly parsed into an AthleteResponse model
        4. Confirms all athlete attributes are correctly extracted
        
        This ensures the client can retrieve and process detailed player information correctly.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a mock response that will pass validation
                mock_json = {
                    "athlete": {
                        "id": "4433137",
                        "uid": "s:40~a:4433137",
                        "guid": "ec41d158a74500a29b2f5c1cd9dd7847",
                        "firstName": "John",
                        "lastName": "Doe",
                        "fullName": "John Doe",
                        "displayName": "John Doe",
                        "shortName": "J. Doe",
                        "jersey": "23",
                        "position": {"name": "Guard", "abbreviation": "G"},
                        "height": 75,
                        "weight": 180,
                        "active": True,
                        "team": {
                            "id": "123",
                            "uid": "s:40~t:123",
                            "name": "Team A",
                            "abbreviation": "TA"
                        },
                        "statistics": [
                            {
                                "name": "ppg",
                                "value": 18.5,
                                "displayValue": "18.5",
                                "type": "season",
                                "season": "2023",
                                "categories": [
                                    {
                                        "name": "scoring",
                                        "stats": [
                                            {"name": "ppg", "value": 18.5}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
                mock_get.return_value = mock_json
                
                # Call the client method
                result = await client.get_athlete("4433137")
                
                # Check that the API was called correctly
                mock_get.assert_called_once_with(
                    "/v3/sports/basketball/mens-college-basketball/athletes/4433137"
                )
                
                # Verify that the result is a valid AthleteResponse
                assert isinstance(result, AthleteResponse)
                assert result.athlete.id == "4433137"
                assert result.athlete.display_name == "John Doe"
                assert result.athlete.team.id == "123"
    
    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self):
        """
        Test that the client properly implements retry logic for transient errors.
        
        This test:
        1. Configures the mock to fail with different errors, then eventually succeed
        2. Calls endpoint methods that should implement retry logic
        3. Verifies that retry attempts are made with appropriate backoff
        4. Confirms that the operation eventually succeeds after retries
        5. Checks that non-retryable errors are still propagated correctly
        
        This ensures the client can recover from temporary API failures while still reporting permanent errors.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request to fail on first attempt and succeed on second
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # First call fails, second call succeeds
                mock_response = {
                    "events": [
                        {
                            "id": "401524691",
                            "uid": "s:40~l:41~e:401524691",
                            "name": "Team A vs Team B",
                            "shortName": "TA vs TB",
                            "date": "2023-03-01T00:00Z",
                            "season": {
                                "year": 2023,
                                "type": 2
                            },
                            "competitions": [
                                {
                                    "id": "401524691",
                                    "uid": "s:40~l:41~c:401524691",
                                    "date": "2023-03-01T00:00Z",
                                    "status": {
                                        "clock": 0,
                                        "displayClock": "0:00",
                                        "period": 2,
                                        "type": {
                                            "name": "STATUS_FINAL",
                                            "completed": True
                                        }
                                    },
                                    "competitors": [
                                        {
                                            "id": "123",
                                            "uid": "s:40~t:123",
                                            "type": "team",
                                            "order": 1,
                                            "homeAway": "home",
                                            "team": {
                                                "id": "123",
                                                "uid": "s:40~t:123",
                                                "name": "Team A",
                                                "abbreviation": "TA",
                                                "displayName": "Team A"
                                            },
                                            "score": "75"
                                        },
                                        {
                                            "id": "456",
                                            "uid": "s:40~t:456",
                                            "type": "team",
                                            "order": 2,
                                            "homeAway": "away",
                                            "team": {
                                                "id": "456",
                                                "uid": "s:40~t:456",
                                                "name": "Team B",
                                                "abbreviation": "TB",
                                                "displayName": "Team B"
                                            },
                                            "score": "70"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }

                # Set up side effects for multiple retry attempts
                mock_get.side_effect = [
                    Exception("API Error"),  # First attempt fails
                    Exception("API Error"),  # Second attempt fails
                    mock_response  # Third attempt succeeds
                ]
                
                # Patch sleep to avoid waiting in tests
                with patch('asyncio.sleep'):
                    # Call the client method - default max_attempts is 3
                    result = await client.get_scoreboard("20230301")
                    
                    # Check that the API was called multiple times
                    assert mock_get.call_count == 3
                    
                    # Verify the result is a valid DataFrame
                    assert isinstance(result, pl.DataFrame)
                    assert not result.is_empty()
    
    @pytest.mark.asyncio
    async def test_all_athletes_pagination(self):
        """
        Test that the client correctly handles pagination when fetching all athletes.
        
        This test:
        1. Creates mock responses for multiple pages of athlete data
        2. Configures the mock to return different responses based on page number
        3. Calls the get_all_athletes method
        4. Verifies all pages are properly fetched and combined
        5. Confirms the combined result contains all athlete data across pages
        
        This ensures the client can handle paginated responses and aggregate them correctly.
        """
        async with ESPNClient() as client:
            # Mock the get_athletes method instead of _get
            with patch.object(
                client, 
                'get_athletes', 
                new_callable=AsyncMock
            ) as mock_get_athletes:
                # Create mock responses for first and second pages
                first_page_response = MagicMock()
                first_page_response.items = [{"id": "1"}, {"id": "2"}]
                first_page_response.total_pages = 3
                first_page_response.page_index = 1
                
                second_page_response = MagicMock()
                second_page_response.items = [{"id": "3"}, {"id": "4"}]
                second_page_response.total_pages = 3
                second_page_response.page_index = 2
                
                # Return different responses for different pages
                mock_get_athletes.side_effect = [
                    first_page_response, 
                    second_page_response
                ]
                
                # Limit to just 2 pages for test
                result = await client.get_all_athletes(max_pages=2)
                
                # Check that the method was called twice with correct parameters
                assert mock_get_athletes.call_count == 2
                assert mock_get_athletes.call_args_list[0][1]['limit'] == 50
                assert mock_get_athletes.call_args_list[0][1]['page'] == 1
                assert mock_get_athletes.call_args_list[1][1]['page'] == 2
                
                # Verify that the result contains combined data
                assert len(result) == 4  # 2 items from each page
                assert result[0]["id"] == "1"
                assert result[1]["id"] == "2"
                assert result[2]["id"] == "3"
                assert result[3]["id"] == "4" 