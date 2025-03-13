import json
import os

import polars as pl
import pytest

from src.data.collection.espn.models import (
    GameSummaryResponse,
    TeamResponse,
    TeamsResponse,
)
from src.data.collection.espn.parsers import (
    parse_game_summary,
    parse_team_data,
    parse_teams_list,
)


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

class TestParsers:
    def test_parse_game_summary(self, load_fixture):
        """Test parsing game summary response."""
        # Load and validate fixture data
        data = {
            "boxscore": {
                "teams": [
                    {
                        "team": {
                            "id": "130",
                            "displayName": "Michigan Wolverines"
                        },
                        "statistics": [
                            {"name": "points", "displayValue": "87"},
                            {"name": "rebounds", "displayValue": "35"}
                        ]
                    },
                    {
                        "team": {
                            "id": "275",
                            "displayName": "Wisconsin Badgers"
                        },
                        "statistics": [
                            {"name": "points", "displayValue": "79"},
                            {"name": "rebounds", "displayValue": "30"}
                        ]
                    }
                ],
                "players": [
                    {
                        "team": {"id": "130"},
                        "statistics": [
                            {
                                "athletes": [
                                    {
                                        "athlete": {
                                            "id": "1234",
                                            "displayName": "John Doe"
                                        },
                                        "stats": [
                                            {"name": "points", "displayValue": "20"},
                                            {"name": "rebounds", "displayValue": "10"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "plays": [
                {
                    "id": "401479672-1",
                    "clock": {"displayValue": "19:45"},
                    "period": {"number": 1},
                    "text": "John Doe made Three Point Jumper",
                    "scoringPlay": True,
                    "scoreValue": 3,
                    "team": {"id": "130"},
                    "coordinate": {"x": 25, "y": 15}
                }
            ]
        }
        
        response = GameSummaryResponse.model_validate(data)
        result = parse_game_summary(response)
        
        # Test team stats DataFrame
        assert "team_stats" in result
        team_stats = result["team_stats"]
        assert isinstance(team_stats, pl.DataFrame)
        assert len(team_stats) == 2
        assert all(col in team_stats.columns for col in [
            "team_id", "team_name", "points", "rebounds"
        ])
        
        # Test player stats DataFrame
        assert "player_stats" in result
        player_stats = result["player_stats"]
        assert isinstance(player_stats, pl.DataFrame)
        assert len(player_stats) == 1
        assert all(col in player_stats.columns for col in [
            "team_id", "player_id", "player_name", "points", "rebounds"
        ])
        
        # Test plays DataFrame
        assert "plays" in result
        plays = result["plays"]
        assert isinstance(plays, pl.DataFrame)
        assert len(plays) == 1
        assert all(col in plays.columns for col in [
            "id", "clock", "period", "text", "scoring_play", "score_value",
            "team_id", "coordinate_x", "coordinate_y"
        ])
    
    def test_parse_team_data(self):
        """Test parsing team response."""
        data = {
            "team": {
                "id": "130",
                "uid": "s:40~l:41~t:130",
                "location": "Michigan",
                "name": "Wolverines",
                "abbreviation": "MICH",
                "displayName": "Michigan Wolverines",
                "color": "00274C",
                "alternateColor": "ffcb05",
                "logos": [
                    {
                        "href": "https://a.espncdn.com/i/teamlogos/ncaa/500/130.png",
                        "width": 500,
                        "height": 500
                    }
                ]
            }
        }
        
        response = TeamResponse.model_validate(data)
        result = parse_team_data(response)
        
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 1
        
        # Get the first row as a dictionary
        row = result.to_dicts()[0]
        assert row["id"] == "130"
        assert row["name"] == "Wolverines"
        assert row["location"] == "Michigan"
        assert row["display_name"] == "Michigan Wolverines"
        assert row["logo_url"] == "https://a.espncdn.com/i/teamlogos/ncaa/500/130.png"
    
    def test_parse_teams_list(self):
        """Test parsing teams list response."""
        data = {
            "sports": [
                {
                    "leagues": [
                        {
                            "teams": [
                                {
                                    "id": "130",
                                    "name": "Wolverines",
                                    "location": "Michigan",
                                    "abbreviation": "MICH",
                                    "displayName": "Michigan Wolverines",
                                    "color": "00274C",
                                    "alternateColor": "ffcb05",
                                    "logos": [
                                        {
                                            "href": "https://a.espncdn.com/i/teamlogos/ncaa/500/130.png"
                                        }
                                    ],
                                    "groups": {
                                        "name": "Big Ten",
                                        "division": "East"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        response = TeamsResponse.model_validate(data)
        result = parse_teams_list(response)
        
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 1
        
        # Get the first row as a dictionary
        row = result.to_dicts()[0]
        assert row["id"] == "130"
        assert row["name"] == "Wolverines"
        assert row["location"] == "Michigan"
        assert row["display_name"] == "Michigan Wolverines"
        assert row["conference"] == "Big Ten"
        assert row["division"] == "East" 