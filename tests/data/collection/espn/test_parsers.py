import json
import os
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.data.collection.espn.client import ESPNClient
from src.data.collection.espn.models import (
    GameSummaryResponse,
    RankingsResponse,
    RosterResponse,
    ScoreboardResponse,
    TeamResponse,
    TeamsResponse,
)
from src.data.collection.espn.parsers import (
    parse_game_summary,
    parse_rankings,
    parse_scoreboard,
    parse_team_data,
    parse_team_roster,
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
        assert team_stats.shape[0] == 2
        assert "team_id" in team_stats.columns
        assert "points" in team_stats.columns
        assert "rebounds" in team_stats.columns
        
        # Test player stats DataFrame
        assert "player_stats" in result
        player_stats = result["player_stats"]
        assert isinstance(player_stats, pl.DataFrame)
        assert "player_id" in player_stats.columns
        assert "team_id" in player_stats.columns
        
        # Test plays DataFrame
        assert "plays" in result
        plays = result["plays"]
        assert isinstance(plays, pl.DataFrame)
        assert "play_id" in plays.columns
        assert "period" in plays.columns
        assert "text" in plays.columns
    
    def test_parse_team_data(self):
        """Test parsing team data response."""
        data = {
            "team": {
                "id": "52",
                "uid": "s:40~l:41~t:52",
                "slug": "air-force-falcons",
                "location": "Air Force",
                "name": "Falcons",
                "nickname": "Air Force",
                "abbreviation": "AFA",
                "displayName": "Air Force Falcons",
                "color": "004a7b",
                "alternateColor": "d9e3ef",
                "logos": [
                    {"href": "https://a.espncdn.com/i/teamlogos/ncaa/500/52.png"}
                ]
            }
        }
        
        response = TeamResponse.model_validate(data)
        result = parse_team_data(response)
        
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert "team_id" in result.columns
        assert "team_name" in result.columns
        assert "abbreviation" in result.columns
        assert "logo_url" in result.columns
        assert result[0, "team_id"] == "52"
        assert result[0, "team_name"] == "Air Force Falcons"
        assert result[0, "abbreviation"] == "AFA"
    
    def test_parse_teams_list(self):
        """Test parsing teams list response."""
        data = {
            "sports": [
                {
                    "id": "40",
                    "leagues": [
                        {
                            "id": "41",
                            "teams": [
                                {
                                    "team": {
                                        "id": "52",
                                        "uid": "s:40~l:41~t:52",
                                        "location": "Air Force",
                                        "name": "Falcons",
                                        "abbreviation": "AFA",
                                        "displayName": "Air Force Falcons",
                                        "logos": [
                                            {"href": "https://a.espncdn.com/i/teamlogos/ncaa/500/52.png"}
                                        ]
                                    }
                                },
                                {
                                    "team": {
                                        "id": "2",
                                        "uid": "s:40~l:41~t:2",
                                        "location": "Alabama",
                                        "name": "Crimson Tide",
                                        "abbreviation": "ALA",
                                        "displayName": "Alabama Crimson Tide",
                                        "logos": [
                                            {"href": "https://a.espncdn.com/i/teamlogos/ncaa/500/2.png"}
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ],
            "pageCount": 10,
            "pageIndex": 1,
            "pageSize": 25,
            "count": 250
        }
        
        response = TeamsResponse.model_validate(data)
        result = parse_teams_list(response)
        
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 2
        assert "team_id" in result.columns
        assert "team_name" in result.columns
        assert "abbreviation" in result.columns
        assert result[0, "team_id"] == "52"
        assert result[1, "team_id"] == "2"
        assert result[0, "team_name"] == "Air Force Falcons"
        assert result[1, "team_name"] == "Alabama Crimson Tide"
    
    def test_parse_scoreboard(self):
        """Test parsing scoreboard response."""
        data = {
            "events": [
                {
                    "id": "401479672",
                    "uid": "s:40~l:41~e:401479672",
                    "date": "2023-03-01T00:00Z",
                    "name": "Wisconsin Badgers at Michigan Wolverines",
                    "shortName": "WIS @ MICH",
                    "competitions": [
                        {
                            "id": "401479672",
                            "uid": "s:40~l:41~e:401479672~c:401479672",
                            "date": "2023-03-01T00:00Z",
                            "competitors": [
                                {
                                    "id": "130",
                                    "uid": "s:40~l:41~t:130",
                                    "type": "team",
                                    "order": 1,
                                    "homeAway": "home",
                                    "team": {
                                        "id": "130",
                                        "uid": "s:40~l:41~t:130",
                                        "displayName": "Michigan Wolverines"
                                    },
                                    "score": "87"
                                },
                                {
                                    "id": "275",
                                    "uid": "s:40~l:41~t:275",
                                    "type": "team",
                                    "order": 2,
                                    "homeAway": "away",
                                    "team": {
                                        "id": "275",
                                        "uid": "s:40~l:41~t:275",
                                        "displayName": "Wisconsin Badgers"
                                    },
                                    "score": "79"
                                }
                            ],
                            "status": {
                                "clock": 0,
                                "displayClock": "0:00",
                                "period": 2,
                                "type": {
                                    "state": "post",
                                    "name": "STATUS_FINAL",
                                    "completed": True
                                }
                            }
                        }
                    ],
                    "season": {
                        "year": 2023,
                        "type": 2
                    }
                }
            ]
        }
        
        response = ScoreboardResponse.model_validate(data)
        result = parse_scoreboard(response)
        
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert "game_id" in result.columns
        assert "home_team_id" in result.columns
        assert "away_team_id" in result.columns
        assert "home_score" in result.columns
        assert "away_score" in result.columns
        assert "status" in result.columns
        assert result[0, "game_id"] == "401479672"
        assert result[0, "home_team_id"] == "130"
        assert result[0, "away_team_id"] == "275"
        assert result[0, "home_score"] == "87"
        assert result[0, "away_score"] == "79"

    def test_empty_scoreboard(self):
        """Test parsing empty scoreboard response."""
        data = {"events": []}
        
        response = ScoreboardResponse.model_validate(data)
        result = parse_scoreboard(response)
        
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert "game_id" in result.columns
        assert "date" in result.columns
        assert "home_team_id" in result.columns
        assert "home_team_name" in result.columns
        assert "away_team_id" in result.columns
        assert "away_team_name" in result.columns
        assert "home_score" in result.columns
        assert "away_score" in result.columns

    # Add more comprehensive parser tests for all parsers
    @pytest.mark.parametrize("parser_func,expected_columns", [
        (
            lambda x: ESPNClient()._process_scoreboard_data(x), 
            ["game_id", "home_team_name", "away_team_name"]
        ),
        (parse_team_data, ["team_id", "team_name", "abbreviation"]),
        (parse_teams_list, ["team_id", "team_name", "abbreviation"]),
    ])
    def test_parser_empty_inputs(self, parser_func, expected_columns):
        """Test parsers handle empty inputs gracefully."""
        # For some parsers, we need specific empty structures
        if parser_func == parse_game_summary:
            data = GameSummaryResponse.model_validate({
                "boxscore": {"teams": [], "players": []},
                "plays": []
            })
        elif parser_func == parse_team_data:
            # For team data, we need minimal valid data as empty isn't an option
            data = TeamResponse.model_validate({
                "team": {
                    "id": "", "uid": "", "displayName": ""
                }
            })
        elif parser_func == parse_teams_list:
            data = TeamsResponse.model_validate({
                "sports": [], 
                "pageCount": 0, 
                "pageIndex": 0, 
                "pageSize": 0, 
                "count": 0
            })
        elif callable(parser_func) and parser_func.__name__ == "<lambda>":
            # This is the process_scoreboard_data lambda function
            data = ScoreboardResponse.model_validate({"events": []})
        else:
            # For other parsers, use appropriate empty model
            if parser_func in [parse_scoreboard, ESPNClient()._process_scoreboard_data]:
                data = ScoreboardResponse.model_validate({"events": []})
            else:
                # Default empty dict case
                data = {}
        
        # Call the parser
        result = parser_func(data)
        
        # Check result is a DataFrame or Dict of DataFrames
        if isinstance(result, dict):
            # For parsers returning multiple DataFrames
            for _df_name, df in result.items():
                assert isinstance(df, pl.DataFrame)
        else:
            # For parsers returning a single DataFrame
            assert isinstance(result, pl.DataFrame)
            
            # For empty inputs, result should either be empty or have default schema
            # Skip the column check if it's a completely empty DataFrame (0 columns)
            if result.shape[0] == 0 and result.shape[1] > 0:
                for col in expected_columns:
                    assert col in result.columns

class TestESPNParsers:
    """Test the ESPN API client parser functions."""
    
    def test_parse_scoreboard(self):
        """Test parsing scoreboard data."""
        # Create a mock response model
        mock_response = MagicMock(spec=ScoreboardResponse)
        mock_event = MagicMock()
        mock_event.id = "401524691"
        mock_event.uid = "s:40~l:41~e:401524691"
        mock_event.name = "Team A vs Team B"
        mock_event.date = "2023-03-01T00:00Z"
        mock_event.season = MagicMock()
        mock_event.season.year = 2023
        mock_event.season.type = 2
        
        mock_competition = MagicMock()
        mock_competition.id = "401524691"
        mock_competition.uid = "s:40~l:41~e:401524691~c:401524691"
        mock_competition.date = "2023-03-01T00:00Z"
        mock_competition.status = MagicMock()
        mock_competition.status.type = {"state": "post", "completed": True}
        mock_competition.status.period = 2
        
        mock_competitor1 = MagicMock()
        mock_competitor1.id = "123"
        mock_competitor1.uid = "s:40~l:41~t:123"
        mock_competitor1.type = "team"
        mock_competitor1.order = 1
        mock_competitor1.home_away = "home"
        mock_competitor1.team = MagicMock()
        mock_competitor1.team.id = "123"
        mock_competitor1.team.uid = "s:40~l:41~t:123"
        mock_competitor1.team.display_name = "Team A"
        mock_competitor1.score = "75"
        
        mock_competitor2 = MagicMock()
        mock_competitor2.id = "456"
        mock_competitor2.uid = "s:40~l:41~t:456"
        mock_competitor2.type = "team"
        mock_competitor2.order = 2
        mock_competitor2.home_away = "away"
        mock_competitor2.team = MagicMock()
        mock_competitor2.team.id = "456"
        mock_competitor2.team.uid = "s:40~l:41~t:456"
        mock_competitor2.team.display_name = "Team B"
        mock_competitor2.score = "70"
        
        mock_competition.competitors = [mock_competitor1, mock_competitor2]
        mock_event.competitions = [mock_competition]
        mock_response.events = [mock_event]
        
        # Call the parser function
        result = parse_scoreboard(mock_response)
        
        # Verify the result
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert "game_id" in result.columns
        assert "home_team_id" in result.columns
        assert "away_team_id" in result.columns
        assert "home_score" in result.columns
        assert "away_score" in result.columns
        assert result[0, "game_id"] == "401524691"
        assert result[0, "home_team_id"] == "123"
        assert result[0, "away_team_id"] == "456"
        assert result[0, "home_score"] == "75"
        assert result[0, "away_score"] == "70"
    
    def test_parse_teams(self):
        """Test parsing teams data."""
        # Create a properly structured mock response
        mock_response = TeamsResponse.model_validate({
            "sports": [
                {
                    "id": "40",
                    "leagues": [
                        {
                            "id": "41",
                            "teams": [
                                {
                                    "team": {
                                        "id": "123",
                                        "uid": "s:40~l:41~t:123",
                                        "location": "Team A",
                                        "name": "Mascot",
                                        "abbreviation": "TA",
                                        "displayName": "Team A Mascot",
                                        "logos": [
                                            {"href": "http://example.com/logo.png"}
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ],
            "pageCount": 1,
            "pageIndex": 1,
            "pageSize": 25,
            "count": 25
        })
        
        # Call the parser function
        result = parse_teams_list(mock_response)
        
        # Verify the result
        assert isinstance(result, pl.DataFrame)
        assert not result.is_empty()
        
        # Check that the expected columns are present
        expected_columns = ["team_id", "team_name", "abbreviation"]
        for col in expected_columns:
            assert col in result.columns
        
        # Check values
        assert result[0, "team_id"] == "123"
        assert result[0, "team_name"] == "Team A Mascot"
        assert result[0, "abbreviation"] == "TA"
    
    def test_parse_team(self):
        """Test parsing single team data."""
        # Create a properly structured mock response
        mock_response = TeamResponse.model_validate({
            "team": {
                "id": "123",
                "uid": "s:40~l:41~t:123",
                "location": "Team A",
                "name": "Mascot",
                "abbreviation": "TA",
                "displayName": "Team A Mascot",
                "color": "000000",
                "alternateColor": "FFFFFF",
                "logos": [
                    {"href": "http://example.com/logo.png"}
                ]
            }
        })
        
        # Call the parser function
        result = parse_team_data(mock_response)
        
        # Verify the result
        assert isinstance(result, pl.DataFrame)
        assert not result.is_empty()
        
        # Check values
        assert result[0, "team_id"] == "123"
        assert result[0, "team_name"] == "Team A Mascot"
        assert result[0, "abbreviation"] == "TA"
        assert result[0, "logo_url"] == "http://example.com/logo.png"
    
    def test_parse_roster(self):
        """Test parsing roster data."""
        # Create a properly structured mock response
        mock_response = RosterResponse.model_validate({
            "team": {
                "id": "123",
                "uid": "s:40~l:41~t:123",
                "location": "Team A",
                "name": "Mascot",
                "abbreviation": "TA",
                "displayName": "Team A Mascot",
                "logos": [
                    {"href": "http://example.com/logo.png"}
                ]
            },
            "roster": [
                {
                    "player": {
                        "id": "4433137",
                        "uid": "s:40~p:4433137",
                        "fullName": "John Doe",
                        "displayName": "John Doe",
                        "firstName": "John",
                        "lastName": "Doe",
                        "jersey": "23",
                        "position": {
                            "name": "Guard",
                            "abbreviation": "G"
                        },
                        "height": "6'3\"",
                        "weight": 180,
                        "age": 21,
                        "collegeName": "State University",
                        "headshot": {
                            "href": "http://example.com/headshot.png"
                        }
                    }
                }
            ]
        })
        
        # Call the parser function
        result = parse_team_roster(mock_response)
        
        # Verify the result
        assert isinstance(result, pl.DataFrame)
        assert not result.is_empty()
        assert result.shape[0] == 1
        
        # Check values
        assert result[0, "player_id"] == "4433137"
        assert result[0, "player_name"] == "John Doe"
        assert result[0, "jersey"] == "23"
        assert result[0, "position"] == "Guard"
    
    def test_parse_game_summary(self):
        """Test parsing game summary data."""
        # Create a properly structured mock response
        mock_response = GameSummaryResponse.model_validate({
            "boxscore": {
                "teams": [
                    {
                        "team": {
                            "id": "123",
                            "uid": "s:40~l:41~t:123",
                            "displayName": "Team A"
                        },
                        "statistics": [
                            {"name": "points", "displayValue": "75"},
                            {"name": "rebounds", "displayValue": "40"}
                        ]
                    },
                    {
                        "team": {
                            "id": "456",
                            "uid": "s:40~l:41~t:456",
                            "displayName": "Team B"
                        },
                        "statistics": [
                            {"name": "points", "displayValue": "70"},
                            {"name": "rebounds", "displayValue": "35"}
                        ]
                    }
                ],
                "players": [
                    {
                        "team": {"id": "123"},
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
                    "team": {"id": "123"},
                    "coordinate": {"x": 25, "y": 15}
                }
            ]
        })
        
        # Call the parser function
        result = parse_game_summary(mock_response)
        
        # Verify the result
        assert isinstance(result, dict)
        assert "team_stats" in result
        assert "player_stats" in result
        assert "plays" in result
        
        # Check team stats
        team_stats = result["team_stats"]
        assert isinstance(team_stats, pl.DataFrame)
        assert team_stats.shape[0] == 2
        assert "team_id" in team_stats.columns
        assert "points" in team_stats.columns
        
        # Check player stats
        player_stats = result["player_stats"]
        assert isinstance(player_stats, pl.DataFrame)
        assert "player_id" in player_stats.columns
        assert "team_id" in player_stats.columns
        
        # Check plays
        plays = result["plays"]
        assert isinstance(plays, pl.DataFrame)
        assert "play_id" in plays.columns
        assert "period" in plays.columns
    
    def test_parse_rankings(self):
        """Test parsing rankings data."""
        # Create a properly structured mock response
        mock_response = RankingsResponse.model_validate({
            "rankings": [
                {
                    "name": "AP Top 25",
                    "shortName": "AP",
                    "type": "poll",
                    "rankings": [
                        {
                            "current": 1,
                            "id": "123",
                            "uid": "s:40~l:41~t:123",
                            "name": "Team A",
                            "nickname": "Mascots",
                            "abbreviation": "TA",
                            "rank": 1,
                            "score": 1550,
                            "record": {"name": "Overall", "summary": "30-2"}
                        },
                        {
                            "current": 2,
                            "id": "456",
                            "uid": "s:40~l:41~t:456",
                            "name": "Team B",
                            "nickname": "Others",
                            "abbreviation": "TB",
                            "rank": 2,
                            "score": 1480,
                            "record": {"name": "Overall", "summary": "28-4"}
                        }
                    ]
                }
            ]
        })
        
        # Call the parser function
        result = parse_rankings(mock_response)
        
        # Verify the result
        assert isinstance(result, pl.DataFrame)
        assert not result.is_empty()
        assert result.shape[0] == 2
        
        # Check values
        assert "poll_name" in result.columns
        assert "poll_type" in result.columns
        assert "team_id" in result.columns
        assert "team_name" in result.columns
        assert "rank" in result.columns
        
        # Check first row
        assert result[0, "poll_name"] == "AP Top 25"
        assert result[0, "poll_type"] == "poll"
        assert result[0, "team_id"] == "123"
        assert result[0, "team_name"] == "Team A"
        assert result[0, "rank"] == 1 