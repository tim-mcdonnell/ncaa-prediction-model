from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Team(BaseModel):
    """Model for team information in ESPN API responses."""
    id: str
    uid: str
    location: str = ""
    name: str = ""
    abbreviation: str = ""
    display_name: str = Field("", alias="displayName")
    logo_url: Optional[str] = Field(None, alias="logos")
    
    def __init__(self, **data):
        # Convert logo list to single URL if present
        logos = data.get("logos")
        if isinstance(logos, list) and logos:
            data["logos"] = logos[0].get("href") if isinstance(logos[0], dict) else None
        super().__init__(**data)

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
    winner: Optional[bool] = None

class Competition(BaseModel):
    """Model for competition information."""
    id: str
    uid: str
    date: datetime
    status: GameStatus
    competitors: List[Competitor]
    venue: Optional[Dict[str, Any]] = None

class Season(BaseModel):
    year: int
    type: int

class Event(BaseModel):
    """Model for event information."""
    id: str
    uid: str
    date: datetime
    name: str
    short_name: str = Field(alias="shortName")
    season: Season
    competitions: List[Competition]

class ScoreboardResponse(BaseModel):
    """Model for scoreboard endpoint response."""
    events: List[Event]

class TeamResponse(BaseModel):
    """Model for team endpoint response."""
    team: Team

class TeamsResponse(BaseModel):
    """Model for teams endpoint response."""
    sports: List[Dict[str, Any]] = []
    pageCount: int = 0
    pageIndex: int = 0
    pageSize: int = 0
    count: int = 0

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

# New models for player and roster data
class Position(BaseModel):
    abbreviation: str = ""
    name: str = ""

class Player(BaseModel):
    id: str
    uid: str = ""
    full_name: str = Field("", alias="fullName")
    display_name: str = Field("", alias="displayName")
    first_name: str = Field("", alias="firstName")
    last_name: str = Field("", alias="lastName")
    jersey: Optional[str] = None
    position: Optional[Position] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    age: Optional[int] = None
    college_name: Optional[str] = Field(None, alias="collegeName")
    birth_place: Optional[Dict[str, str]] = Field(None, alias="birthPlace")
    headshot_url: Optional[str] = Field(None, alias="headshot")
    
    def __init__(self, **data):
        # Handle headshot URL
        headshot = data.get("headshot")
        if isinstance(headshot, dict) and "href" in headshot:
            data["headshot"] = headshot["href"]
        super().__init__(**data)

class RosterItem(BaseModel):
    player: Player

class RosterResponse(BaseModel):
    team: Team
    roster: List[RosterItem] = []
    coach: Optional[List[Dict[str, Any]]] = None

class NewsArticle(BaseModel):
    id: str
    headline: str
    description: str
    published: datetime
    type: str
    images: Optional[List[Dict[str, Any]]] = None
    links: Optional[Dict[str, Any]] = None
    
    def __init__(self, **data):
        # Handle image URL extraction
        images = data.get("images")
        if isinstance(images, list) and images:
            # Keep the original images data for model validation
            pass
        super().__init__(**data)
    
    @property
    def image_url(self) -> Optional[str]:
        """Get the first image URL if available."""
        if self.images and len(self.images) > 0:
            img = self.images[0]
            if isinstance(img, dict) and "url" in img:
                return img["url"]
        return None
    
    @property
    def article_url(self) -> Optional[str]:
        """Get the article URL if available."""
        if self.links and "web" in self.links:
            link = self.links["web"]
            if isinstance(link, dict) and "href" in link:
                return link["href"]
        return None

class NewsResponse(BaseModel):
    articles: List[NewsArticle] = Field([], alias="articles")
    header: Optional[Dict[str, Any]] = None

class RankedTeam(BaseModel):
    id: str
    uid: str
    name: str
    nickname: str
    abbreviation: str
    rank: int
    previous_rank: Optional[int] = Field(None, alias="previousRank")
    score: Optional[float] = None
    record: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    
    def __init__(self, **data):
        # Handle nested team data if present
        if "team" in data:
            team_data = data.pop("team")
            for key, value in team_data.items():
                data[key] = value
                
        # Extract logo URL if present
        logos = data.get("logos")
        if isinstance(logos, list) and logos and "href" in logos[0]:
            data["logo_url"] = logos[0]["href"]
            
        super().__init__(**data)

class RankingGroup(BaseModel):
    name: str
    short_name: str = Field("", alias="shortName")
    type: str
    rankings: List[RankedTeam]

class RankingsResponse(BaseModel):
    rankings: List[RankingGroup] = []

class Conference(BaseModel):
    id: str
    uid: str
    name: str
    short_name: str = Field("", alias="shortName")
    abbreviation: str
    teams: List[Dict[str, Any]] = []
    
class GroupsResponse(BaseModel):
    groups: List[Conference] = Field([], alias="groups")

class TeamStat(BaseModel):
    name: str
    displayValue: str
    value: float

class TeamStanding(BaseModel):
    team: Team
    stats: List[TeamStat] = []

class StandingsType(BaseModel):
    id: str
    name: str
    abbreviation: str
    type: str
    standings: Dict[str, List[TeamStanding]] = {}

class StandingsGroup(BaseModel):
    standings: Dict[str, Any] = {}
    id: str = ""
    name: str = ""
    abbreviation: str = ""
    type: str = ""
    
    @property
    def entries(self) -> List[TeamStanding]:
        """Extract all team standings entries."""
        result = []
        if self.standings and "entries" in self.standings:
            for entry in self.standings["entries"]:
                if "team" in entry:
                    team_data = entry["team"]
                    stats = []
                    
                    if "stats" in entry:
                        for stat in entry["stats"]:
                            stats.append(TeamStat.model_validate(stat))
                    
                    team = Team.model_validate(team_data)
                    team_standing = TeamStanding(team=team, stats=stats)
                    result.append(team_standing)
        return result

class StandingsResponse(BaseModel):
    groups: List[StandingsGroup] = Field([], alias="standings")

class ScheduleGame(BaseModel):
    id: str
    date: datetime
    name: str
    short_name: str = Field("", alias="shortName")
    competition_type: Optional[str] = Field(None, alias="competitionType")

class ScheduleSeason(BaseModel):
    year: int
    display_name: str = Field("", alias="displayName")

class ScheduleItem(BaseModel):
    id: str
    uid: str
    date: datetime
    name: str
    short_name: str = Field("", alias="shortName")
    season: ScheduleSeason
    competitions: List[Dict[str, Any]] = []
    
class ScheduleResponse(BaseModel):
    team: Team
    events: List[ScheduleItem] = []
    season: Optional[ScheduleSeason] = None

class AthleteBio(BaseModel):
    height: Optional[str] = None
    weight: Optional[int] = None
    birth_date: Optional[str] = Field(None, alias="birthDate")
    birth_place: Optional[Dict[str, str]] = Field(None, alias="birthPlace")
    college: Optional[str] = None
    hand: Optional[str] = None

class AthletePosition(BaseModel):
    name: str
    abbreviation: str = ""
    
class AthleteStat(BaseModel):
    name: str
    value: float
    display_value: str = Field("", alias="displayValue")

class Athlete(BaseModel):
    id: str
    uid: str
    guid: str
    first_name: str = Field("", alias="firstName")
    last_name: str = Field("", alias="lastName")
    full_name: str = Field("", alias="fullName")
    display_name: str = Field("", alias="displayName")
    short_name: str = Field("", alias="shortName")
    position: Optional[AthletePosition] = None
    headshot_url: Optional[str] = None
    jersey: Optional[str] = None
    active: bool = True
    bio: Optional[AthleteBio] = None
    team: Optional[Team] = None
    statistics: Optional[List[AthleteStat]] = None

class AthleteResponse(BaseModel):
    athlete: Athlete

class AthletesPageResponse(BaseModel):
    page: int = 1
    page_size: int = Field(0, alias="pageSize") 
    total_pages: int = Field(0, alias="totalPages")
    items: List[Athlete] = []

# Team Statistics Models
class StatisticCategory(BaseModel):
    name: str
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    abbreviation: str

class StatisticValue(BaseModel):
    name: str
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    value: float
    display_value: str = Field("", alias="displayValue")

class TeamStatistic(BaseModel):
    name: str
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    description: Optional[str] = None
    abbreviation: str
    type: str
    summary: str
    stats: List[StatisticValue]

class TeamStatisticsResponse(BaseModel):
    team: Team
    statistics: List[TeamStatistic]

# Tournament Bracket Models
class BracketRegion(BaseModel):
    id: str
    name: str
    short_name: str = Field("", alias="shortName")
    abbreviation: str

class BracketSeed(BaseModel):
    source_id: str = Field("", alias="sourceId")
    source_name: str = Field("", alias="sourceName")
    rank: int
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    is_top: bool = Field(False, alias="isTop")

class BracketTeam(BaseModel):
    id: str
    name: str
    abbreviation: str
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    logo_url: Optional[str] = None
    seed: Optional[BracketSeed] = None
    
    def __init__(self, **data):
        # Handle logo URL extraction
        if "logos" in data and isinstance(data["logos"], list) and data["logos"]:
            data["logo_url"] = data["logos"][0].get("href") if isinstance(data["logos"][0], dict) else None
            del data["logos"]
        super().__init__(**data)

class BracketRecord(BaseModel):
    wins: int
    losses: int
    summary: str
    display_value: str = Field("", alias="displayValue")

class BracketCompetitor(BaseModel):
    id: str
    uid: str
    type: str
    order: int
    home_away: str = Field("", alias="homeAway")
    team: BracketTeam
    score: Optional[str] = None
    winner: Optional[bool] = None
    advancing: Optional[bool] = None
    eliminated: Optional[bool] = None
    record: Optional[BracketRecord] = None
    status: Optional[str] = None

class BracketGameStatus(BaseModel):
    clock: float
    display_clock: str = Field("", alias="displayClock")
    period: int
    type: Dict[str, Any]

class BracketCompetition(BaseModel):
    id: str
    uid: str
    date: datetime
    venue: Optional[Dict[str, Any]] = None
    status: Optional[BracketGameStatus] = None
    competitors: List[BracketCompetitor]
    notes: Optional[List[Dict[str, Any]]] = None
    recent: Optional[bool] = None
    conference_competition: Optional[bool] = Field(None, alias="conferenceCompetition")

class BracketRound(BaseModel):
    number: int
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    competitions: List[BracketCompetition] = []

class BracketTournament(BaseModel):
    id: str
    uid: str
    name: str
    short_name: str = Field("", alias="shortName")
    year: int
    season_type: int = Field(0, alias="seasonType")
    display_name: str = Field("", alias="displayName")
    short_display_name: str = Field("", alias="shortDisplayName")
    regions: List[BracketRegion] = []
    rounds: List[BracketRound] = []

class TournamentResponse(BaseModel):
    tournament: BracketTournament
