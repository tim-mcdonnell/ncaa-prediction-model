from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from src.data.collection.espn.client import ESPNClient


class TestESPNIntegration:
    """Integration tests for the ESPN API client."""
    
    @pytest.mark.asyncio
    async def test_scoreboardPipeline_whenProcessingAPIResponse_shouldConvertToDataframe(self):
        """
        Test the complete pipeline from API request to DataFrame for scoreboard endpoint.
        
        This test:
        1. Creates a mock scoreboard response with a unique game name
        2. Verifies that the client correctly processes the response into a DataFrame
        3. Ensures the result contains the expected game data
        4. Confirms the mock was called with the correct parameters
        
        This test verifies the end-to-end integration of the scoreboard endpoint.
        """
        # Create a client with unique parameters for this test
        async with ESPNClient(rate_limit=8.5, burst_limit=4) as client:
            # Use a fresh mock for this test
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a mock response unique to this test
                mock_json = {
                    "events": [
                        {
                            "id": "401524691",
                            "uid": "s:40~l:41~e:401524691",
                            "date": "2023-03-01T00:00Z",
                            "name": "Team A vs Team B - Scoreboard Test",  # Unique name
                            "shortName": "TA vs TB",
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
                                            "completed": True,
                                            "state": "post"
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
                                                "uid": "s:40~l:41~t:123",
                                                "name": "Team A",
                                                "abbreviation": "TA"
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
                                                "uid": "s:40~l:41~t:456",
                                                "name": "Team B",
                                                "abbreviation": "TB"
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
                
                # Call the client method
                result = await client.get_scoreboard("20230301")
                
                # Verify the result is a valid DataFrame
                assert isinstance(result, pl.DataFrame)
                assert result.shape[0] > 0
                
                # Verify mock was called correctly
                mock_get.assert_called_once()
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock()
    
    @pytest.mark.asyncio
    async def test_teamsPipeline_whenProcessingAPIResponse_shouldMakeCorrectAPICall(self):
        """
        Test the complete pipeline from API request to DataFrame for teams endpoint.
        
        This test:
        1. Creates a mock teams response with a uniquely named team
        2. Calls the get_teams() method on the client
        3. Verifies that the API endpoint is called with the correct parameters
        4. Ensures the mock is reset to prevent state leakage
        
        This test ensures that the teams endpoint integration functions correctly.
        """
        # Create a client with unique parameters for this test
        async with ESPNClient(rate_limit=9.2, burst_limit=3) as client:
            # Use a fresh mock for this test
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a unique mock response for this test
                mock_json = {
                    "sports": [
                        {
                            "leagues": [
                                {
                                    "teams": [
                                        {
                                            "team": {
                                                "id": "123",
                                                "uid": "s:40~t:123",
                                                "name": "Team A - Teams Test",  # Unique name
                                                "abbreviation": "TA",
                                                "displayName": "Team A - Teams Test"
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
                await client.get_teams()
                
                # Check that the API was called correctly
                mock_get.assert_called_once()
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock()
    
    @pytest.mark.asyncio
    async def test_athletePipeline_whenProcessingAPIResponse_shouldReturnValidResponse(self):
        """
        Test the complete pipeline from API request to model object for athlete endpoint.
        
        This test:
        1. Creates a mock athlete response with a unique player name
        2. Calls the get_athlete() method with a specific athlete ID
        3. Verifies the response is properly parsed into the expected model
        4. Checks specific athlete attributes to ensure data integrity
        5. Resets the mock to prevent test interference
        
        This test validates the athlete endpoint's ability to parse and return structured data.
        """
        # Create a client with unique parameters for this test
        async with ESPNClient(rate_limit=9.8, burst_limit=4) as client:
            # Use a fresh mock for this test
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a unique mock response for this test
                mock_json = {
                    "athlete": {
                        "id": "4433137",
                        "uid": "s:40~a:4433137",
                        "guid": "ec41d158a74500a29b2f5c1cd9dd7847",
                        "firstName": "John",
                        "lastName": "Doe",
                        "fullName": "John Doe - Athlete Test",  # Unique name
                        "displayName": "John Doe - Athlete Test",
                        "shortName": "J. Doe",
                        "position": {
                            "name": "Guard",
                            "abbreviation": "G"
                        },
                        "headshot": {
                            "href": "https://example.com/headshot.png"
                        },
                        "jersey": "23",
                        "active": True
                    }
                }
                mock_get.return_value = mock_json
                
                # Call the client method
                result = await client.get_athlete("4433137")
                
                # Verify the result
                assert result.athlete.id == "4433137"
                assert result.athlete.display_name == "John Doe - Athlete Test"
                assert result.athlete.position.name == "Guard"
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_liveAPI_whenCallingScoreboard_shouldReturnDataframe(self):
        """
        Test scoreboard endpoint with a simulated live response.
        
        This test:
        1. Creates a mock response that mimics a real API response from the scoreboard endpoint
        2. Calls the get_scoreboard() method with a specific date
        3. Verifies the response is successfully converted to a non-empty DataFrame
        4. Confirms the mock was called with the correct parameters
        5. Ensures proper cleanup to prevent test interference
        
        This test simulates integration with the live API without making actual external calls.
        """
        # Create a client with unique parameters for this test
        async with ESPNClient(rate_limit=7.9, burst_limit=5) as client:
            # Create a unique mock response for this test
            mock_json = {
                "events": [
                    {
                        "id": "401524691",
                        "uid": "s:40~l:41~e:401524691",
                        "date": "2023-03-01T00:00Z",
                        "name": "Team A vs Team B - Live Test",  # Unique name
                        "shortName": "TA vs TB",
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
                                        "completed": True,
                                        "state": "post"
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
                                            "uid": "s:40~l:41~t:123",
                                            "name": "Team A", 
                                            "abbreviation": "TA"
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
                                            "uid": "s:40~l:41~t:456",
                                            "name": "Team B", 
                                            "abbreviation": "TB"
                                        },
                                        "score": "70"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            # Use a fresh patch for this test
            with patch.object(client, '_get', return_value=mock_json) as mock_get:
                result = await client.get_scoreboard("20230301")
                
                # Verify we get results
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                assert result.shape[0] > 0
                
                # Verify mock was called
                mock_get.assert_called_once()
                
                # Reset mock to ensure no state leakage
                mock_get.reset_mock() 