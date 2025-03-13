import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import polars as pl

from src.utils.resilience.retry import retry

from .models import (
    AthleteResponse,
    AthletesPageResponse,
    GameSummaryResponse,
    GroupsResponse,
    RankingsResponse,
    RosterResponse,
    ScheduleResponse,
    ScoreboardResponse,
    StandingsResponse,
    Team,
    TeamResponse,
    TeamsResponse,
    TeamStatisticsResponse,
    TournamentResponse,
)

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""
    
    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests per second
            burst: Maximum burst size (number of requests that can be made at once)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            time_passed = now - self.last_update
            self.tokens = min(
                self.burst,
                self.tokens + time_passed * self.rate
            )
            
            if self.tokens < 1:
                # Calculate the time needed to get one token
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 1  # We now have exactly one token
            
            self.tokens -= 1
            self.last_update = asyncio.get_event_loop().time()

class ESPNClient:
    """Client for interacting with ESPN's NCAA basketball APIs."""
    
    BASE_URL = "http://site.api.espn.com"
    SPORT = "basketball"
    LEAGUE = "mens-college-basketball"
    
    def __init__(
        self,
        rate_limit: float = 5.0,  # requests per second
        burst_limit: int = 10,
        timeout: float = 30.0,
    ):
        """
        Initialize ESPN client.
        
        Args:
            rate_limit: Number of requests allowed per second
            burst_limit: Maximum number of requests that can be made at once
            timeout: Default timeout for HTTP requests in seconds
        """
        self.rate_limiter = RateLimiter(rate_limit, burst_limit)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            f"Initialized ESPN client with rate_limit={rate_limit}, "
            f"burst_limit={burst_limit}"
        )
    
    async def __aenter__(self) -> 'ESPNClient':
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        logger.debug("ESPN client context entered, HTTP client initialized")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            logger.debug("Closing ESPN client HTTP connection")
            await self._client.aclose()
            self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising an error if not initialized."""
        if self._client is None:
            logger.error("Attempted to use HTTP client before initialization")
            raise RuntimeError(
                "Client not initialized. Use async with ESPNClient() as client: ..."
            )
        return self._client
    
    async def _get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a rate-limited GET request to the ESPN API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            JSON response data
        """
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}{endpoint}"
        logger.debug(f"Making GET request to {url} with params: {params}")
        
        start_time = asyncio.get_event_loop().time()
        response = await self.client.get(url, params=params)
        duration = asyncio.get_event_loop().time() - start_time
        
        logger.debug(
            f"Received response from {url} in {duration:.2f}s "
            f"(status: {response.status_code})"
        )
        
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} from {url}: {str(e)}")
            raise
        
        return response.json()
    
    def _validate_date_format(self, date_str: str) -> bool:
        """
        Validate that the date string is in the correct format (YYYYMMDD) and 
        represents a valid date.
        
        Args:
            date_str: Date string in YYYYMMDD format
            
        Returns:
            True if the date is valid, False otherwise
        """
        if not date_str or not isinstance(date_str, str):
            return False
            
        # Check length and that it's all digits
        if len(date_str) != 8 or not date_str.isdigit():
            return False
            
        try:
            # Try to parse the date
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Use datetime to validate the date
            datetime(year, month, day)
            return True
        except ValueError:
            # This will catch invalid dates like February 31st
            return False
    
    def _parse_date_str(self, date_str: str) -> date:
        """
        Parse a YYYYMMDD date string to a date object.
        
        Args:
            date_str: Date in YYYYMMDD format
            
        Returns:
            Date object
        
        Raises:
            ValueError: If the date string is invalid
        """
        if not self._validate_date_format(date_str):
            raise ValueError(
                f"Invalid date format: {date_str}. "
                f"Expected format is YYYYMMDD with a valid calendar date."
            )
            
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        return date(year, month, day)
    
    def _format_date(self, d: date) -> str:
        """
        Format a date object as a YYYYMMDD string.
        
        Args:
            d: Date object
            
        Returns:
            Formatted date string
        """
        return d.strftime("%Y%m%d")
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_scoreboard(self, date_str: str) -> pl.DataFrame:
        """
        Get scoreboard data for a specific date.
        
        Args:
            date_str: Date in YYYYMMDD format
            
        Returns:
            DataFrame containing game data
            
        Raises:
            ValueError: If the date_str is not a valid date
        """
        # Validate the date format before making the API call
        if not self._validate_date_format(date_str):
            logger.error(f"Invalid date format provided: {date_str}")
            raise ValueError(
                f"Invalid date format: {date_str}. "
                f"Expected format is YYYYMMDD with a valid calendar date."
            )
        
        logger.info(f"Fetching scoreboard data for date: {date_str}")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/scoreboard"
        params = {"dates": date_str}
        
        data = await self._get(endpoint, params)
        response = ScoreboardResponse.model_validate(data)
        
        # Additional validation: if we have events, check that they match the 
        # requested date (This is to catch ESPN API's silent "correction" of 
        # invalid dates)
        if response.events:
            # Parse the requested date
            req_year = int(date_str[0:4])
            req_month = int(date_str[4:6])
            req_day = int(date_str[6:8])
            requested_date = datetime(req_year, req_month, req_day).date()
            
            # Check if any events don't match the requested date
            for event in response.events:
                event_date = event.date.date()
                if event_date != requested_date:
                    logger.warning(
                        f"Date mismatch: Requested games for {requested_date}, "
                        f"but received game on {event_date}. "
                        f"ESPN API may have silently corrected an invalid date."
                    )
                    # Since we already validated the date is correct, this should 
                    # rarely happen. It could happen if ESPN's API has different 
                    # timezone handling
                    break
        
        result_df = self._process_scoreboard_data(response)
        logger.info(f"Retrieved {len(result_df)} games for date {date_str}")
        return result_df
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_scoreboard_for_date_range(
        self, start_date_str: str, end_date_str: str
    ) -> pl.DataFrame:
        """
        Get scoreboard data for a range of dates.
        
        This method fetches game data for all dates in the inclusive range from 
        start_date to end_date. Results from all dates are combined into a single 
        DataFrame.
        
        Args:
            start_date_str: Start date in YYYYMMDD format
            end_date_str: End date in YYYYMMDD format
            
        Returns:
            DataFrame containing game data for all dates in the range
            
        Raises:
            ValueError: If either date string is invalid or if end_date is before 
                start_date
        """
        # Parse and validate dates
        start_date = self._parse_date_str(start_date_str)
        end_date = self._parse_date_str(end_date_str)
        
        # Validate date range
        if end_date < start_date:
            logger.error(
                f"Invalid date range: end date {end_date} is before start date "
                f"{start_date}"
            )
            raise ValueError(
                f"Invalid date range: end date {end_date_str} is before "
                f"start date {start_date_str}"
            )
        
        date_diff = (end_date - start_date).days
        logger.info(
            f"Fetching scoreboard data for date range {start_date_str} to "
            f"{end_date_str} ({date_diff + 1} days)"
        )
        
        # List to store DataFrames for each date
        all_frames = []
        current_date = start_date
        
        # Loop through each date in the range
        while current_date <= end_date:
            current_date_str = self._format_date(current_date)
            try:
                df = await self.get_scoreboard(current_date_str)
                if not df.is_empty():
                    all_frames.append(df)
                    logger.info(f"Added {len(df)} games from {current_date_str}")
                else:
                    logger.info(f"No games found for {current_date_str}")
            except Exception as e:
                logger.error(f"Error fetching data for {current_date_str}: {str(e)}")
                # Continue to next date even if there's an error
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Combine all dataframes
        if not all_frames:
            logger.warning(
                f"No games found for date range {start_date_str} to {end_date_str}"
            )
            # Return empty DataFrame with correct schema
            return pl.DataFrame(schema={
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
        
        combined_df = pl.concat(all_frames)
        logger.info(
            f"Successfully retrieved {len(combined_df)} total games for date range "
            f"{start_date_str} to {end_date_str}"
        )
        return combined_df
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_game_summary(self, game_id: str) -> GameSummaryResponse:
        """
        Get detailed game summary.
        
        Args:
            game_id: ESPN game ID
            
        Returns:
            Game summary response object
        """
        logger.info(f"Fetching game summary for game ID: {game_id}")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/summary"
        params = {"event": game_id}
        
        data = await self._get(endpoint, params)
        response = GameSummaryResponse.model_validate(data)
        logger.info(f"Retrieved game summary for game ID {game_id}")
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_team(self, team_id: str) -> TeamResponse:
        """
        Get team information.
        
        Args:
            team_id: ESPN team ID
            
        Returns:
            Team response object
        """
        logger.info(f"Fetching team data for team ID: {team_id}")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/teams/{team_id}"
        data = await self._get(endpoint)
        response = TeamResponse.model_validate(data)
        logger.info(
            f"Retrieved team data for {response.team.display_name} (ID: {team_id})"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_teams(self, page: int = 1) -> TeamsResponse:
        """
        Get list of teams with pagination.
        
        Args:
            page: Page number for pagination
            
        Returns:
            Teams response object
        """
        logger.info(f"Fetching teams list (page {page})")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/teams"
        params = {"page": page}
        
        data = await self._get(endpoint, params)
        response = TeamsResponse.model_validate(data)
        
        # Log team count without including the entire response
        team_count = 0
        if response.sports and response.sports[0].get("leagues"):
            for league in response.sports[0]["leagues"]:
                if league.get("teams"):
                    team_count += len(league["teams"])
        
        logger.info(f"Retrieved {team_count} teams on page {page}")
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_all_teams(self) -> List[Team]:
        """
        Get all teams across all pages.
        
        This method automatically handles pagination and combines results from all 
        pages. ESPN's API typically returns 50 teams per page, and this method will 
        continue fetching pages until it reaches a page with fewer than 50 teams or 
        no teams, indicating it has retrieved all teams.
        
        Returns:
            List of Team objects containing all teams
        """
        logger.info("Fetching all teams with automatic pagination")
        
        # Get the first page
        current_page = 1
        response = await self.get_teams(page=current_page)
        
        # Extract teams from the nested structure
        all_teams = []
        if response.sports and response.sports[0].get("leagues"):
            for league in response.sports[0]["leagues"]:
                if league.get("teams"):
                    for team_entry in league["teams"]:
                        if "team" in team_entry:
                            # Convert dictionary to Team object
                            team_data = team_entry["team"]
                            team = Team.model_validate(team_data)
                            all_teams.append(team)
        
        # Get the number of teams in the first page to use for comparison
        page_size = len(all_teams)
        if page_size == 0:
            logger.warning("No teams found in the first page")
            return all_teams
            
        # Continue fetching pages until we get a page with fewer items than the 
        # page size (indicating it's the last page)
        while True:
            current_page += 1
            logger.info(f"Fetching teams page {current_page}")
            
            response = await self.get_teams(page=current_page)
            
            # Extract teams from this page
            page_teams = []
            if response.sports and response.sports[0].get("leagues"):
                for league in response.sports[0]["leagues"]:
                    if league.get("teams"):
                        for team_entry in league["teams"]:
                            if "team" in team_entry:
                                # Convert dictionary to Team object
                                team_data = team_entry["team"]
                                team = Team.model_validate(team_data)
                                page_teams.append(team)
            
            # If we got no teams or fewer teams than the page size, we've reached the 
            # last page
            if not page_teams or len(page_teams) < page_size:
                if page_teams:
                    all_teams.extend(page_teams)
                    logger.info(
                        f"Reached final page {current_page} with "
                        f"{len(page_teams)} teams"
                    )
                else:
                    logger.info(f"Reached empty page {current_page}")
                break
                
            all_teams.extend(page_teams)
            
        logger.info(
            f"Fetched a total of {len(all_teams)} teams across {current_page} pages"
        )
        return all_teams
    
    def _process_scoreboard_data(self, response: ScoreboardResponse) -> pl.DataFrame:
        """
        Process scoreboard response into a DataFrame.
        
        Args:
            response: Validated scoreboard response
            
        Returns:
            DataFrame containing game data
        """
        records = []
        
        for event in response.events:
            for competition in event.competitions:
                home_team = next(
                    c for c in competition.competitors if c.home_away == "home"
                )
                away_team = next(
                    c for c in competition.competitors if c.home_away == "away"
                )
                
                record = {
                    "game_id": event.id,
                    "date": event.date,
                    "name": event.name,
                    "home_team_id": home_team.team.id,
                    "home_team_name": home_team.team.display_name,
                    "home_team_score": home_team.score,
                    "away_team_id": away_team.team.id,
                    "away_team_name": away_team.team.display_name,
                    "away_team_score": away_team.score,
                    "status": competition.status.type["name"],
                    "period": competition.status.period,
                    "season_year": event.season.year,
                    "season_type": event.season.type
                }
                records.append(record)
        
        return pl.DataFrame(records)
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_team_roster(self, team_id: str) -> RosterResponse:
        """
        Get team roster information.
        
        Args:
            team_id: Team ID
            
        Returns:
            Roster response object
        """
        logger.info(f"Fetching roster data for team ID: {team_id}")
        endpoint = (
            f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/teams/"
            f"{team_id}/roster"
        )
        
        data = await self._get(endpoint)
        response = RosterResponse.model_validate(data)
        
        player_count = len(response.roster) if response.roster else 0
        logger.info(
            f"Retrieved roster with {player_count} players for team ID: {team_id}"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_rankings(self) -> RankingsResponse:
        """
        Get current NCAA basketball team rankings.
        
        Returns:
            Rankings response object containing ranking groups and ranked teams
        """
        logger.info("Fetching current NCAA basketball rankings")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/rankings"
        
        data = await self._get(endpoint)
        response = RankingsResponse.model_validate(data)
        
        group_count = len(response.rankings) if response.rankings else 0
        logger.info(f"Retrieved {group_count} ranking groups")
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_conferences(self) -> GroupsResponse:
        """
        Get NCAA basketball conferences/groups.
        
        Returns:
            Groups response object containing conference information
        """
        logger.info("Fetching NCAA basketball conferences")
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/groups"
        
        data = await self._get(endpoint)
        response = GroupsResponse.model_validate(data)
        
        conference_count = len(response.groups) if response.groups else 0
        logger.info(f"Retrieved {conference_count} conferences")
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_standings(self, group_id: Optional[str] = None) -> StandingsResponse:
        """
        Get standings for NCAA basketball.
        
        Args:
            group_id: Optional conference/group ID to filter standings
            
        Returns:
            Standings response object containing team standings by conference
        """
        logger.info(
            f"Fetching NCAA basketball standings"
            f"{' for group: ' + group_id if group_id else ''}"
        )
        endpoint = f"/apis/v2/sports/{self.SPORT}/{self.LEAGUE}/standings"
        params = {"group": group_id} if group_id else None
        
        data = await self._get(endpoint, params)
        response = StandingsResponse.model_validate(data)
        
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_team_schedule(
        self, 
        team_id: str, 
        season: Optional[int] = None, 
        season_type: Optional[int] = None
    ) -> ScheduleResponse:
        """
        Get team schedule.
        
        Args:
            team_id: Team ID
            season: Season year (e.g., 2023)
            season_type: Season type (e.g., 2 for regular season)
            
        Returns:
            Schedule response object
        """
        logger.info(
            f"Fetching schedule for team ID: {team_id}" +
            (f" (season: {season})" if season else "") +
            (f" (type: {season_type})" if season_type else "")
        )
        
        endpoint = (
            f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/teams/"
            f"{team_id}/schedule"
        )
        params = {}
        
        if season:
            params["season"] = season
        if season_type:
            params["seasontype"] = season_type
        
        data = await self._get(endpoint, params)
        response = ScheduleResponse.model_validate(data)
        
        logger.info(
            f"Retrieved {len(response.events)} events for team ID: {team_id}"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_athlete(self, athlete_id: str) -> AthleteResponse:
        """
        Get detailed information for a specific athlete.
        
        Args:
            athlete_id: Athlete ID
            
        Returns:
            Athlete response object containing player details
        """
        logger.info(f"Fetching data for athlete ID: {athlete_id}")
        
        endpoint = f"/v3/sports/{self.SPORT}/{self.LEAGUE}/athletes/{athlete_id}"
        
        data = await self._get(endpoint)
        response = AthleteResponse.model_validate(data)
        
        logger.info(
            f"Retrieved data for athlete: {response.athlete.display_name} "
            f"(ID: {athlete_id})"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_athletes(
        self, 
        limit: int = 50, 
        page: int = 1
    ) -> AthletesPageResponse:
        """
        Get list of athletes with pagination.
        
        Args:
            limit: Maximum number of athletes per page
            page: Page number to retrieve
            
        Returns:
            AthletesPageResponse object containing paginated athlete data
        """
        logger.info(f"Fetching athletes (page {page}, limit {limit})")
        
        endpoint = f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/athletes"
        params = {"limit": limit, "page": page}
        
        data = await self._get(endpoint, params)
        response = AthletesPageResponse.model_validate(data)
        
        athlete_count = len(response.items) if response.items else 0
        logger.info(
            f"Retrieved {athlete_count} athletes (page {page} "
            f"of {response.total_pages})"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_all_athletes(
        self, 
        limit_per_page: int = 50, 
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all athletes across all pages.
        
        This method automatically handles pagination and combines results 
        from all pages.
        
        Args:
            limit_per_page: Number of athletes per page
            max_pages: Maximum number of pages to fetch (None for all pages)
            
        Returns:
            List of athlete data dictionaries
        """
        logger.info(f"Fetching all athletes with pagination (limit: {limit_per_page})")
        
        # Get the first page
        current_page = 1
        response = await self.get_athletes(limit=limit_per_page, page=current_page)
        
        # Extract all athletes from the first page
        all_athletes = list(response.items)
        
        # If only one page, return early
        if response.total_pages <= 1 or (max_pages is not None and max_pages <= 1):
            return all_athletes
        
        # Continue fetching pages until we've retrieved all pages or reached max_pages
        max_page_to_fetch = (
            response.total_pages if max_pages is None 
            else min(max_pages, response.total_pages)
        )
        
        while current_page < max_page_to_fetch:
            current_page += 1
            logger.info(f"Fetching athletes page {current_page} of {max_page_to_fetch}")
            
            try:
                page_response = await self.get_athletes(
                    limit=limit_per_page, 
                    page=current_page
                )
                if page_response.items:
                    all_athletes.extend(page_response.items)
                    logger.info(
                        f"Added {len(page_response.items)} athletes "
                        f"from page {current_page}"
                    )
                else:
                    logger.info(f"No athletes found on page {current_page}")
            except Exception as e:
                logger.error(f"Error fetching athletes page {current_page}: {str(e)}")
                # Continue to next page even if there's an error
        
        logger.info(f"Successfully retrieved a total of {len(all_athletes)} athletes")
        return all_athletes
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_team_statistics(self, team_id: str) -> TeamStatisticsResponse:
        """
        Get team statistics.
        
        Args:
            team_id: Team ID
            
        Returns:
            Team statistics response object containing detailed team stats
        """
        logger.info(f"Fetching statistics for team ID: {team_id}")
        
        endpoint = (
            f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/teams/"
            f"{team_id}/statistics"
        )
        
        data = await self._get(endpoint)
        response = TeamStatisticsResponse.model_validate(data)
        
        stat_count = len(response.statistics) if response.statistics else 0
        logger.info(
            f"Retrieved {stat_count} statistics categories for team: "
            f"{response.team.display_name} (ID: {team_id})"
        )
        return response
    
    @retry(max_attempts=3, backoff_factor=2.0)
    async def get_tournament_bracket(
        self, 
        year: Optional[int] = None
    ) -> TournamentResponse:
        """
        Get NCAA tournament bracket data.
        
        Args:
            year: Tournament year (e.g., 2023 for 2023 NCAA Tournament). 
                If None, gets the current/latest tournament.
            
        Returns:
            Tournament response object
        """
        logger.info(f"Fetching NCAA tournament bracket{f' for {year}' if year else ''}")
        
        endpoint = (
            f"/apis/site/v2/sports/{self.SPORT}/{self.LEAGUE}/"
            f"tournaments/ncaa-mens"
        )
        params = {"year": year} if year else None
        
        data = await self._get(endpoint, params)
        response = TournamentResponse.model_validate(data)
        
        tournament_name = response.tournament.name
        round_count = len(response.tournament.rounds)
        
        logger.info(
            f"Retrieved tournament bracket for {tournament_name} "
            f"with {round_count} rounds"
        )
        return response
