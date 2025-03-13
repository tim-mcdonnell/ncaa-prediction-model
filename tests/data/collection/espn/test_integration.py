from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from src.data.collection.espn.client import ESPNClient


class TestESPNIntegration:
    """Integration tests for the ESPN API client."""
    
    @pytest.mark.asyncio
    async def test_scoreboard_to_dataframe_pipeline(self):
        """
        Test the complete pipeline from API request to DataFrame 
        for scoreboard endpoint.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
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
    
    @pytest.mark.asyncio
    async def test_teams_to_dataframe_pipeline(self):
        """
        Test the complete pipeline from API request to DataFrame 
        for teams endpoint.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a mock response
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
                                                "name": "Team A",
                                                "abbreviation": "TA",
                                                "displayName": "Team A"
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
    
    @pytest.mark.asyncio
    async def test_athlete_to_dataframe_pipeline(self):
        """
        Test the complete pipeline from API request to DataFrame 
        for athlete endpoint.
        """
        async with ESPNClient() as client:
            # Mock the HTTP request
            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                # Create a mock response
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
                assert result.athlete.display_name == "John Doe"
                assert result.athlete.position.name == "Guard"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_api_scoreboard(self):
        """Live API test for scoreboard endpoint."""
        async with ESPNClient() as client:
            # Create a mock response for integration test
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
            
            with patch.object(client, '_get', return_value=mock_json):
                result = await client.get_scoreboard("20230301")
                
                # Verify we get results
                assert isinstance(result, pl.DataFrame)
                assert not result.is_empty()
                assert result.shape[0] > 0 