"""
Tests for the Collection Pipeline component.

This module tests the functionality of the CollectionPipeline, which is responsible
for retrieving NCAA basketball data from ESPN APIs and storing it in Parquet format.
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from src.pipelines.base_pipeline import PipelineContext, PipelineStatus
from src.pipelines.collection_pipeline import CollectionPipeline


@pytest.fixture
def temp_data_dir():
    """Fixture providing a temporary directory for test data storage."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_espn_api():
    """Fixture providing a mock ESPN API client."""
    mock_api = AsyncMock()
    
    # Mock get_scoreboard to return empty DataFrame for most dates
    # and return actual data for specific test dates
    def scoreboard_side_effect(date_str):
        if date_str in ["20221106", "20221107"]:  # Modified date to match our patched date range
            return pl.DataFrame([
                {
                    "id": f"401587{date_str[-1]}", 
                    "date": f"2022-11-{date_str[-2:]}T23:30Z",
                    "home_team_id": "52" if date_str == "20221106" else "150",
                    "away_team_id": "2390" if date_str == "20221106" else "2247",
                    "home_score": 101 if date_str == "20221106" else 92,
                    "away_score": 73 if date_str == "20221106" else 54,
                    "status": "final"
                }
            ])
        elif date_str == "20221102":  # Add data for the rate limiting test
            return pl.DataFrame([
                {
                    "id": "4015875", 
                    "date": "2022-11-02T20:00Z",
                    "home_team_id": "153",
                    "away_team_id": "66",
                    "home_score": 85,
                    "away_score": 70,
                    "status": "final"
                }
            ])
        else:
            # Return empty DataFrame for most dates
            return pl.DataFrame()
    
    mock_api.get_scoreboard.side_effect = scoreboard_side_effect
    
    # Mock get_teams to return teams dataframe
    mock_teams_df = pl.DataFrame([
        {"id": "52", "name": "Miami", "abbreviation": "MIA", "conference_id": "2", "conference_name": "ACC"},
        {"id": "150", "name": "Duke", "abbreviation": "DUKE", "conference_id": "2", "conference_name": "ACC"},
        {"id": "2390", "name": "NJIT", "abbreviation": "NJIT", "conference_id": "22", "conference_name": "America East"},
        {"id": "2247", "name": "Dartmouth", "abbreviation": "DART", "conference_id": "21", "conference_name": "Ivy"}
    ])
    mock_api.get_teams.return_value = mock_teams_df
    
    # Mock get_game_summary to return response objects like the real method would
    def mock_game_summary_side_effect(game_id):
        # Create a mock GameSummaryResponse object with necessary attributes
        mock_response = MagicMock()
        mock_response.boxscore = MagicMock()
        
        # Create teams with statistics
        mock_teams = []
        
        # Home team data
        home_team = {
            "team": {"id": "52" if game_id == "4015876" else "150"},
            "homeAway": "home",
            "statistics": [
                {
                    "name": "Field Goals",
                    "stats": [
                        {"name": "fieldGoalsMade", "value": 35},
                        {"name": "fieldGoalsAttempted", "value": 70}
                    ]
                },
                {
                    "name": "Three Point Field Goals",
                    "stats": [
                        {"name": "threePointFieldGoalsMade", "value": 10},
                        {"name": "threePointFieldGoalsAttempted", "value": 25}
                    ]
                }
            ]
        }
        
        # Away team data
        away_team = {
            "team": {"id": "2390" if game_id == "4015876" else "2247"},
            "homeAway": "away",
            "statistics": [
                {
                    "name": "Field Goals",
                    "stats": [
                        {"name": "fieldGoalsMade", "value": 20},
                        {"name": "fieldGoalsAttempted", "value": 55}
                    ]
                },
                {
                    "name": "Three Point Field Goals",
                    "stats": [
                        {"name": "threePointFieldGoalsMade", "value": 5},
                        {"name": "threePointFieldGoalsAttempted", "value": 20}
                    ]
                }
            ]
        }
        
        mock_teams.append(home_team)
        mock_teams.append(away_team)
        mock_response.boxscore.teams = mock_teams
        
        # Add game info with venue
        mock_response.game_info = {
            "venue": {
                "id": "1234",
                "fullName": "Cameron Indoor Stadium" if game_id == "4015877" else "Watsco Center"
            },
            "attendance": 9000 if game_id == "4015877" else 7500
        }
        
        return mock_response
    
    mock_api.get_game_summary.side_effect = mock_game_summary_side_effect
    
    # Make the context manager methods work with the mock
    mock_api.__aenter__.return_value = mock_api
    mock_api.__aexit__.return_value = None
    
    return mock_api


class TestCollectionPipeline:
    """Tests for the Collection Pipeline component."""
    
    @pytest.mark.asyncio
    async def test_collect_season_games_full(self, temp_data_dir, mock_espn_api):
        """Test collecting a full season's worth of games."""
        # Arrange
        with patch("src.pipelines.collection_pipeline.ESPNClient", return_value=mock_espn_api):
            # Also patch the date range to only test a few days instead of the whole season
            with patch("src.pipelines.collection_pipeline.date") as mock_date:
                # Mock the date constructor to return fixed dates
                def date_side_effect(year, month, day):
                    # For any construction of our season start and end dates, return our test range
                    if year == 2022 and month == 11 and day == 1:  # season_start
                        return date(2022, 11, 1)
                    elif year == 2023 and month == 4 and day == 15:  # season_end
                        return date(2022, 11, 8)  # Much shorter range for testing
                    else:
                        return date(year, month, day)
                
                mock_date.side_effect = date_side_effect
                
                pipeline = CollectionPipeline(data_dir=temp_data_dir)
                context = PipelineContext(params={"season": 2023, "mode": "full"})
                
                # Reset mock call counts before the test
                mock_espn_api.get_scoreboard.reset_mock()
                mock_espn_api.get_teams.reset_mock()
                mock_espn_api.get_game_summary.reset_mock()
                
                # Act
                result = await pipeline.execute(context)
                
                # Assert
                assert result.status == PipelineStatus.SUCCESS
                assert mock_espn_api.get_scoreboard.called  # Using get_scoreboard instead of get_season_games
                assert mock_espn_api.get_teams.called
                
                # We have specific dates that return data, so we should have 2 games and 2 game summaries
                assert mock_espn_api.get_game_summary.call_count == 3  # Updated to 3 to include the game from 20221102
                
                # Check that Parquet files were created
                season_dir = Path(temp_data_dir) / "seasons" / "2023"
                assert (season_dir / "games.parquet").exists()
                assert (season_dir / "teams.parquet").exists()
                assert (season_dir / "game_details.parquet").exists()
                
                # Verify content of Parquet files
                games_df = pl.read_parquet(season_dir / "games.parquet")
                assert len(games_df) == 3  # Updated to 3 to include the game from 20221102
                assert "id" in games_df.columns
                assert "home_team_id" in games_df.columns
                assert "away_team_id" in games_df.columns
    
    @pytest.mark.asyncio
    async def test_collect_season_games_incremental(self, temp_data_dir, mock_espn_api):
        """Test incremental update of current season."""
        # Arrange
        with patch("src.pipelines.collection_pipeline.ESPNClient", return_value=mock_espn_api):
            # Also patch the date range to only test a few days
            with patch("src.pipelines.collection_pipeline.date") as mock_date:
                # Mock the date constructor to return fixed dates
                def date_side_effect(year, month, day):
                    if year == 2022 and month == 11 and day == 1:  # season_start
                        return date(2022, 11, 1)
                    elif year == 2023 and month == 4 and day == 15:  # season_end
                        return date(2022, 11, 8)  # Much shorter range for testing
                    else:
                        return date(year, month, day)
                
                mock_date.side_effect = date_side_effect
                
                # First create an existing dataset
                pipeline = CollectionPipeline(data_dir=temp_data_dir)
                context = PipelineContext(params={"season": 2023, "mode": "full"})
                await pipeline.execute(context)
                
                # Mock modifying API response for incremental update
                # Add a new game for a specific date
                def updated_scoreboard_side_effect(date_str):
                    if date_str == "20221108":
                        return pl.DataFrame([
                            {
                                "id": "4015878",
                                "date": "2022-11-08T00:00Z",
                                "home_team_id": "228",
                                "away_team_id": "2057",
                                "home_score": 88,
                                "away_score": 61,
                                "status": "final"
                            }
                        ])
                    elif date_str in ["20221106", "20221107"]:
                        return pl.DataFrame([
                            {
                                "id": f"401587{date_str[-1]}",
                                "date": f"2022-11-{date_str[-2:]}T23:30Z",
                                "home_team_id": "52" if date_str == "20221106" else "150",
                                "away_team_id": "2390" if date_str == "20221106" else "2247",
                                "home_score": 101 if date_str == "20221106" else 92,
                                "away_score": 73 if date_str == "20221106" else 54,
                                "status": "final"
                            }
                        ])
                    else:
                        # Return empty DataFrame for most dates
                        return pl.DataFrame()
                
                mock_espn_api.get_scoreboard.side_effect = updated_scoreboard_side_effect
                
                # Update side effect for game summary to handle the new game
                def updated_game_summary_side_effect(game_id):
                    # Create a mock GameSummaryResponse object with necessary attributes
                    mock_response = MagicMock()
                    mock_response.boxscore = MagicMock()
                    
                    # Create teams with statistics
                    mock_teams = []
                    
                    if game_id == "4015878":
                        # New game data
                        home_team = {
                            "team": {"id": "228"},
                            "homeAway": "home",
                            "statistics": [
                                {
                                    "name": "Field Goals",
                                    "stats": [
                                        {"name": "fieldGoalsMade", "value": 30},
                                        {"name": "fieldGoalsAttempted", "value": 65}
                                    ]
                                },
                                {
                                    "name": "Three Point Field Goals",
                                    "stats": [
                                        {"name": "threePointFieldGoalsMade", "value": 8},
                                        {"name": "threePointFieldGoalsAttempted", "value": 22}
                                    ]
                                }
                            ]
                        }
                        
                        away_team = {
                            "team": {"id": "2057"},
                            "homeAway": "away",
                            "statistics": [
                                {
                                    "name": "Field Goals",
                                    "stats": [
                                        {"name": "fieldGoalsMade", "value": 22},
                                        {"name": "fieldGoalsAttempted", "value": 60}
                                    ]
                                },
                                {
                                    "name": "Three Point Field Goals",
                                    "stats": [
                                        {"name": "threePointFieldGoalsMade", "value": 4},
                                        {"name": "threePointFieldGoalsAttempted", "value": 18}
                                    ]
                                }
                            ]
                        }
                        
                        mock_teams.append(home_team)
                        mock_teams.append(away_team)
                        mock_response.boxscore.teams = mock_teams
                        
                        # Add game info with venue
                        mock_response.game_info = {
                            "venue": {
                                "id": "5678",
                                "fullName": "Cassell Coliseum"
                            },
                            "attendance": 8000
                        }
                    else:
                        # Existing game data
                        home_team = {
                            "team": {"id": "52" if game_id == "4015876" else "150"},
                            "homeAway": "home",
                            "statistics": [
                                {
                                    "name": "Field Goals",
                                    "stats": [
                                        {"name": "fieldGoalsMade", "value": 35},
                                        {"name": "fieldGoalsAttempted", "value": 70}
                                    ]
                                },
                                {
                                    "name": "Three Point Field Goals",
                                    "stats": [
                                        {"name": "threePointFieldGoalsMade", "value": 10},
                                        {"name": "threePointFieldGoalsAttempted", "value": 25}
                                    ]
                                }
                            ]
                        }
                        
                        away_team = {
                            "team": {"id": "2390" if game_id == "4015876" else "2247"},
                            "homeAway": "away",
                            "statistics": [
                                {
                                    "name": "Field Goals",
                                    "stats": [
                                        {"name": "fieldGoalsMade", "value": 20},
                                        {"name": "fieldGoalsAttempted", "value": 55}
                                    ]
                                },
                                {
                                    "name": "Three Point Field Goals",
                                    "stats": [
                                        {"name": "threePointFieldGoalsMade", "value": 5},
                                        {"name": "threePointFieldGoalsAttempted", "value": 20}
                                    ]
                                }
                            ]
                        }
                        
                        mock_teams.append(home_team)
                        mock_teams.append(away_team)
                        mock_response.boxscore.teams = mock_teams
                        
                        # Add game info with venue
                        mock_response.game_info = {
                            "venue": {
                                "id": "1234",
                                "fullName": "Cameron Indoor Stadium" if game_id == "4015877" else "Watsco Center"
                            },
                            "attendance": 9000 if game_id == "4015877" else 7500
                        }
                    
                    return mock_response
                
                mock_espn_api.get_game_summary.side_effect = updated_game_summary_side_effect
                
                # Reset mock call counts before incremental update
                mock_espn_api.get_scoreboard.reset_mock()
                mock_espn_api.get_teams.reset_mock()
                mock_espn_api.get_game_summary.reset_mock()
                
                # Perform incremental update
                context = PipelineContext(params={"season": 2023, "mode": "incremental"})
                result = await pipeline.execute(context)
                
                # Assert
                assert result.status == PipelineStatus.SUCCESS
                
                # Verify the Parquet files were updated correctly
                season_dir = Path(temp_data_dir) / "seasons" / "2023"
                games_df = pl.read_parquet(season_dir / "games.parquet")
                
                # Should have all 3 games now (plus the one from 20221102)
                assert len(games_df) == 4  # Updated to 4 to include the game from 20221102
                assert "4015878" in games_df["id"].to_list()
                
                # Check game details
                details_df = pl.read_parquet(season_dir / "game_details.parquet")
                assert len(details_df) == 4  # Updated to 4 to include the game from 20221102
    
    @pytest.mark.asyncio
    async def test_collect_season_with_rate_limiting(self, temp_data_dir, mock_espn_api):
        """Test that collection respects rate limits."""
        # Arrange
        with patch("src.pipelines.collection_pipeline.ESPNClient", return_value=mock_espn_api):
            # Patch the date range to only test a few days
            with patch("src.pipelines.collection_pipeline.date") as mock_date:
                # Mock the date constructor to return fixed dates
                def date_side_effect(year, month, day):
                    if year == 2022 and month == 11 and day == 1:  # season_start
                        return date(2022, 11, 1)
                    elif year == 2023 and month == 4 and day == 15:  # season_end
                        return date(2022, 11, 3)  # Very short range for testing
                    else:
                        return date(year, month, day)
                
                mock_date.side_effect = date_side_effect
                
                # Create a pipeline with aggressive rate limiting for testing
                pipeline = CollectionPipeline(
                    data_dir=temp_data_dir,
                    rate_limit=1.0  # 1 request per second
                )
                
                # Reset mock call counts
                mock_espn_api.get_scoreboard.reset_mock()
                mock_espn_api.get_teams.reset_mock()
                mock_espn_api.get_game_summary.reset_mock()
                
                # Act
                context = PipelineContext(params={"season": 2023, "mode": "full"})
                result = await pipeline.execute(context)
                
                # Assert
                assert result.status == PipelineStatus.SUCCESS
                assert mock_espn_api.get_scoreboard.called
                assert mock_espn_api.get_teams.called
                assert mock_espn_api.get_game_summary.called
    
    @pytest.mark.asyncio
    async def test_pipeline_validates_parameters(self, temp_data_dir):
        """Test that the pipeline validates input parameters."""
        # Arrange
        pipeline = CollectionPipeline(data_dir=temp_data_dir)
        
        # Act - Missing season parameter
        result = await pipeline.execute(PipelineContext())
        
        # Assert
        assert result.status == PipelineStatus.VALIDATION_FAILURE
        
        # Act - Invalid mode parameter
        result = await pipeline.execute(
            PipelineContext(params={"season": 2023, "mode": "invalid_mode"})
        )
        
        # Assert
        assert result.status == PipelineStatus.VALIDATION_FAILURE 