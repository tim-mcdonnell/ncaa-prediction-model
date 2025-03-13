from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Team(BaseModel):
    """Model for team information in ESPN API responses."""
    id: str
    uid: str
    location: str
    name: str
    abbreviation: str
    display_name: str = Field(alias="displayName")
    color: Optional[str] = None
    alternate_color: Optional[str] = Field(default=None, alias="alternateColor")
    logos: Optional[List[Dict[str, Any]]] = None

class GameStatus(BaseModel):
    """Model for game status information."""
    clock: float
    display_clock: str = Field(alias="displayClock")
    period: int
    type: Dict[str, Any]

class Competitor(BaseModel):
    """Model for competitor information in a game."""
    id: str
    uid: str
    type: str
    order: int
    home_away: str = Field(alias="homeAway")
    team: Team
    score: Optional[str] = None
    records: Optional[List[Dict[str, Any]]] = None

class Competition(BaseModel):
    """Model for competition information."""
    id: str
    uid: str
    date: datetime
    status: GameStatus
    competitors: List[Competitor]
    venue: Optional[Dict[str, Any]] = None

class Event(BaseModel):
    """Model for event information."""
    id: str
    uid: str
    date: datetime
    name: str
    short_name: str = Field(alias="shortName")
    season: Dict[str, Any]
    competitions: List[Competition]

class ScoreboardResponse(BaseModel):
    """Model for scoreboard endpoint response."""
    events: List[Event]

class TeamResponse(BaseModel):
    """Model for team endpoint response."""
    team: Team

class TeamsResponse(BaseModel):
    """Model for teams endpoint response."""
    sports: List[Dict[str, Any]]  # Complex nested structure, simplified for now

class BoxScore(BaseModel):
    """Model for game summary boxscore."""
    teams: List[Dict[str, Any]]  # Complex nested structure, simplified for now
    players: Optional[List[Dict[str, Any]]] = None

class GameSummaryResponse(BaseModel):
    """Model for game summary endpoint response."""
    boxscore: BoxScore
    game_info: Optional[Dict[str, Any]] = Field(default=None, alias="gameInfo")
    plays: Optional[List[Dict[str, Any]]] = None
    leaders: Optional[List[Dict[str, Any]]] = None
    win_probability: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="winprobability"
    )
