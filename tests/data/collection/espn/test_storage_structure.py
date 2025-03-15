import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from src.data.collection.espn.client import ESPNClient


@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
        "fixtures", 
        "espn_responses"
    )


@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file from the fixtures directory."""
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load


@pytest.mark.asyncio
class TestDataStorageStructure:
    """Test the new consolidated data storage structure."""
    
    async def test_espn_client_debug_flag(self):
        """
        Test that the ESPN client accepts and processes the debug flag parameter.
        
        Verifies:
        1. The client constructor accepts a debug flag
        2. The debug flag is accessible as a property
        """
        # Create client with debug mode enabled
        async with ESPNClient(debug=True) as client:
            assert client.debug is True
            
        # Create client with debug mode disabled (default)
        async with ESPNClient() as client:
            assert client.debug is False
    
    @pytest.mark.parametrize("debug_mode", [True, False])
    async def test_client_get_with_debug_flag(self, debug_mode, load_fixture, tmp_path):
        """
        Test that the client's _get method correctly handles the debug flag.
        
        Verifies:
        1. When debug=True, raw responses are saved to the temp directory
        2. When debug=False, no raw responses are saved
        """
        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        
        # Create a temp path for debug files
        debug_dir = tmp_path / "debug_data" / "2023"
        
        # Setup client and patch the get method
        with patch("httpx.AsyncClient.get", return_value=mock_response), \
             patch("tempfile.gettempdir", return_value=str(tmp_path)):
            
            async with ESPNClient(debug=debug_mode) as client:
                await client._get("test_endpoint", {"date": "20230101"})
                
                # Check if debug file was created
                debug_file = debug_dir / "test_endpoint_20230101.json"
                
                if debug_mode:
                    assert debug_file.exists(), "Debug file should exist when debug=True"
                    with open(debug_file, "r") as f:
                        saved_data = json.load(f)
                    assert saved_data == {"test": "data"}
                else:
                    assert not debug_file.exists(), "Debug file should not exist when debug=False"
    
    async def test_season_consolidation(self, tmp_path):
        """
        Test that the collection process consolidates data into season files.
        
        Verifies:
        1. Data from multiple dates is consolidated into a single season file
        2. The structure follows data/seasons/{season}/games.parquet
        """
        # Define mock data for two dates
        mock_data1 = {
            "events": [
                {
                    "id": "game1",
                    "date": "2023-01-01T12:00Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "game1",
                            "competitors": [
                                {"id": "teamA", "homeAway": "home", "score": "75", "team": {"displayName": "Team A"}},
                                {"id": "teamB", "homeAway": "away", "score": "65", "team": {"displayName": "Team B"}},
                            ],
                            "status": {"type": {"name": "STATUS_FINAL", "completed": True}},
                        }
                    ],
                }
            ]
        }
        
        mock_data2 = {
            "events": [
                {
                    "id": "game2",
                    "date": "2023-01-02T12:00Z",
                    "name": "Team C vs Team D",
                    "competitions": [
                        {
                            "id": "game2",
                            "competitors": [
                                {"id": "teamC", "homeAway": "home", "score": "80", "team": {"displayName": "Team C"}},
                                {"id": "teamD", "homeAway": "away", "score": "70", "team": {"displayName": "Team D"}},
                            ],
                            "status": {"type": {"name": "STATUS_FINAL", "completed": True}},
                        }
                    ],
                }
            ]
        }
        
        # Create a custom mock for the fetch_scoreboard function
        async def mock_fetch_scoreboard(client, date_str, **kwargs):
            if date_str == "20230101":
                return mock_data1
            elif date_str == "20230102":
                return mock_data2
            return {"events": []}
        
        # Import the collection function
        from src.data.collect_ncaa_data import collect_date_range
        
        # Override data directory with temp path
        with patch("src.data.collect_ncaa_data.fetch_scoreboard", side_effect=mock_fetch_scoreboard), \
             patch("src.data.collect_ncaa_data.DATA_DIR", str(tmp_path)), \
             patch("src.data.collect_ncaa_data.SEASONS_DIR", str(tmp_path / "seasons")):
            
            # Run collection for date range
            await collect_date_range(
                "20230101", 
                "20230102",
                rate_limit=0,
                max_retries=1,
                debug=False
            )
            
            # Check that consolidated file was created
            # January dates are part of the previous season (2022)
            season_dir = tmp_path / "seasons" / "2022"
            games_file = season_dir / "games.parquet"
            
            assert games_file.exists(), "Consolidated games file should exist"
            
            # Read the file and verify content
            games_df = pl.read_parquet(games_file)
            assert games_df.shape[0] == 2, "Should contain data from both dates"
            assert set(games_df["id"].to_list()) == {"game1", "game2"}, "Should contain both game IDs"
            
            # Verify that no individual date files were created
            targeted_dir = tmp_path / "targeted_collection"
            if targeted_dir.exists():
                date_files = list(targeted_dir.glob("games_2023*.parquet"))
                assert len(date_files) == 0, "Should not create individual date files"
    
    async def test_debug_json_storage(self, tmp_path):
        """
        Test that the debug flag stores raw JSON in the tmp directory.
        
        Verifies:
        1. When debug=True, JSON is stored in tmp directory
        2. When debug=False, no debug files are created
        """
        # Import the collection function
        from src.data.collect_ncaa_data import fetch_scoreboard
        
        # Mock date and response
        date_str = "20230101"
        mock_data = {"test": "data", "events": []}
        
        # Create a proper mock for the client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        
        # Set up the get method to return the mock response
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Mock tempfile.gettempdir
        temp_dir = str(tmp_path)
        
        with patch("tempfile.gettempdir", return_value=temp_dir):
            # Fetch with debug = True
            result = await fetch_scoreboard(
                mock_client, 
                date_str,
                debug=True
            )
            
            # Check for debug file
            debug_dir = Path(temp_dir) / "debug_data" / "2023"
            debug_file = debug_dir / f"response_{date_str}.json"
            
            assert debug_file.exists(), "Debug file should exist when debug=True"
            with open(debug_file, "r") as f:
                saved_data = json.load(f)
            assert saved_data == mock_data
            
            # Remove the file for clean test
            debug_file.unlink()
            
            # Now fetch with debug = False
            result = await fetch_scoreboard(
                mock_client, 
                date_str,
                debug=False
            )
            
            # Verify no new debug file was created
            assert not debug_file.exists(), "Debug file should not exist when debug=False"
                
    async def test_incremental_update(self, tmp_path):
        """
        Test that incremental updates work with the new consolidated storage structure.
        
        Verifies:
        1. New games are added to existing consolidated files
        2. Duplicate games are updated with latest data
        """
        # Create a season directory and existing games file
        # January dates are part of the previous season (2022)
        season_dir = tmp_path / "seasons" / "2022"
        season_dir.mkdir(parents=True, exist_ok=True)
        
        # Create an existing games file with one game
        existing_game = {
            "id": "game1",
            "date": "2023-01-01T12:00Z",
            "name": "Team A vs Team B",
            "home_team_id": "teamA",
            "home_team_name": "Team A",
            "away_team_id": "teamB",
            "away_team_name": "Team B",
            "home_score": 75,
            "away_score": 65,
            "status": "Final",
            "collection_timestamp": datetime.now().timestamp() - 86400  # Yesterday
        }
        
        existing_df = pl.DataFrame([existing_game])
        existing_df.write_parquet(season_dir / "games.parquet")
        
        # Define mock data with an updated game and a new game
        mock_data_jan1 = {
            "events": [
                {
                    "id": "game1",  # Same ID as existing game
                    "date": "2023-01-01T12:00Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "game1",
                            "competitors": [
                                {"id": "teamA", "homeAway": "home", "score": "80", "team": {"displayName": "Team A"}},  # Score updated
                                {"id": "teamB", "homeAway": "away", "score": "65", "team": {"displayName": "Team B"}},
                            ],
                            "status": {"type": {"name": "STATUS_FINAL", "completed": True}},
                        }
                    ],
                }
            ]
        }
        
        mock_data_jan2 = {
            "events": [
                {
                    "id": "game2",  # New game
                    "date": "2023-01-02T12:00Z",
                    "name": "Team C vs Team D",
                    "competitions": [
                        {
                            "id": "game2",
                            "competitors": [
                                {"id": "teamC", "homeAway": "home", "score": "90", "team": {"displayName": "Team C"}},
                                {"id": "teamD", "homeAway": "away", "score": "85", "team": {"displayName": "Team D"}},
                            ],
                            "status": {"type": {"name": "STATUS_FINAL", "completed": True}},
                        }
                    ],
                }
            ]
        }
        
        # Create a custom mock for the fetch_scoreboard function
        async def mock_fetch_scoreboard(client, date_str, **kwargs):
            if date_str == "20230101":
                return mock_data_jan1
            elif date_str == "20230102":
                return mock_data_jan2
            return {"events": []}
        
        # Import and patch the necessary functions
        with patch("src.data.collect_ncaa_data.fetch_scoreboard", side_effect=mock_fetch_scoreboard), \
             patch("src.data.collect_ncaa_data.DATA_DIR", str(tmp_path)), \
             patch("src.data.collect_ncaa_data.SEASONS_DIR", str(tmp_path / "seasons")):
            
            # Run the collection with incremental update
            from src.data.collect_ncaa_data import collect_date_range
            await collect_date_range(
                "20230101",
                "20230102",
                rate_limit=0,
                max_retries=1,
                debug=False,
                incremental=True  # Use incremental update
            )
            
            # Read the updated file
            updated_df = pl.read_parquet(season_dir / "games.parquet")
            
            # Debug output
            print(f"Updated DataFrame shape: {updated_df.shape}")
            print(f"Updated DataFrame contents:\n{updated_df}")
            print(f"Game IDs in DataFrame: {updated_df['id'].to_list()}")
            
            # Verify file contains both games
            assert updated_df.shape[0] == 2, "Should contain both games"
            assert "game1" in updated_df["id"].to_list(), "Should contain the updated game"
            assert "game2" in updated_df["id"].to_list(), "Should contain the new game"
            
            # Verify the score was updated for game1
            game1_row = updated_df.filter(pl.col("id") == "game1")
            assert game1_row["home_score"][0] == 80, "Home score should be updated"
    
    async def test_game_details_collection(self, tmp_path):
        """
        Test that game details are collected and stored in the consolidated structure.
        
        Verifies:
        1. Game details are collected and stored in game_details.parquet
        2. The details include important statistics and venue information
        """
        # Define mock data for a scoreboard response
        scoreboard_mock = {
            "events": [
                {
                    "id": "game1",
                    "date": "2023-01-01T12:00Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "game1",
                            "competitors": [
                                {"id": "teamA", "homeAway": "home", "score": "75", "team": {"displayName": "Team A"}},
                                {"id": "teamB", "homeAway": "away", "score": "65", "team": {"displayName": "Team B"}},
                            ],
                            "status": {"type": {"name": "STATUS_FINAL", "completed": True}},
                        }
                    ],
                }
            ]
        }
        
        # Define mock data for game details response
        game_details_mock = {
            "gameInfo": {
                "venue": {
                    "id": "venue1",
                    "fullName": "Test Arena"
                },
                "attendance": 15000
            },
            "boxscore": {
                "teams": [
                    {
                        "team": {"id": "teamA"},
                        "homeAway": "home",
                        "statistics": [
                            {
                                "stats": [
                                    {"name": "field goals made", "displayValue": "25"},
                                    {"name": "field goals attempted", "displayValue": "50"},
                                    {"name": "field goal pct", "displayValue": "50.0"},
                                    {"name": "rebounds", "displayValue": "30"}
                                ]
                            }
                        ]
                    },
                    {
                        "team": {"id": "teamB"},
                        "homeAway": "away",
                        "statistics": [
                            {
                                "stats": [
                                    {"name": "field goals made", "displayValue": "22"},
                                    {"name": "field goals attempted", "displayValue": "55"},
                                    {"name": "field goal pct", "displayValue": "40.0"},
                                    {"name": "rebounds", "displayValue": "25"}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        
        # Create a custom mock for the fetch_scoreboard function
        async def mock_fetch_scoreboard(client, date_str, **kwargs):
            return scoreboard_mock
        
        # Create a custom mock for the fetch_game_details function
        async def mock_fetch_game_details(client, game_id, **kwargs):
            return game_details_mock
        
        # Import the collection function
        from src.data.collect_ncaa_data import collect_date_range
        
        # Override data directory and mock the fetch functions
        with patch("src.data.collect_ncaa_data.fetch_scoreboard", side_effect=mock_fetch_scoreboard), \
             patch("src.data.collect_ncaa_data.fetch_game_details", side_effect=mock_fetch_game_details), \
             patch("src.data.collect_ncaa_data.DATA_DIR", str(tmp_path)), \
             patch("src.data.collect_ncaa_data.SEASONS_DIR", str(tmp_path / "seasons")):
            
            # Run collection for date range
            await collect_date_range(
                "20230101", 
                "20230101",
                rate_limit=0,
                max_retries=1,
                debug=False
            )
            
            # Check that game_details file was created
            # January dates are part of the previous season (2022)
            season_dir = tmp_path / "seasons" / "2022"
            game_details_file = season_dir / "game_details.parquet"
            
            assert game_details_file.exists(), "Game details file should exist"
            
            # Read the file and verify content
            details_df = pl.read_parquet(game_details_file)
            
            # Check structure
            assert details_df.shape[0] == 1, "Should contain one game detail entry"
            assert "id" in details_df.columns, "Should have game ID column"
            assert "venue_id" in details_df.columns, "Should have venue ID column"
            assert "venue_name" in details_df.columns, "Should have venue name column"
            assert "attendance" in details_df.columns, "Should have attendance column"
            assert "home_field_goals_made" in details_df.columns, "Should have home statistics"
            assert "away_field_goals_made" in details_df.columns, "Should have away statistics"
            
            # Verify values
            assert details_df[0, "venue_name"] == "Test Arena", "Venue name should match mock data"
            assert details_df[0, "attendance"] == 15000, "Attendance should match mock data"
            assert details_df[0, "home_field_goals_made"] == 25, "Home field goals should match mock data"
            assert details_df[0, "away_field_goals_made"] == 22, "Away field goals should match mock data"
            assert details_df[0, "home_field_goal_pct"] == 50.0, "Home FG percentage should match mock data" 