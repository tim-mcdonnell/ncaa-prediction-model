"""
ESPN API Client

This module provides a client for interacting with ESPN's API to retrieve
NCAA basketball data including games, teams, venues, and statistics.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from src.utils.resilience.retry import retry

logger = logging.getLogger(__name__)


class ESPNAPIError(Exception):
    """Exception raised for ESPN API errors."""
    pass


class RateLimitExceededError(ESPNAPIError):
    """Exception raised when ESPN API rate limit is exceeded."""
    pass


class ESPNClient:
    """
    Client for interacting with ESPN's API.
    
    This client handles API requests for NCAA basketball data, including
    rate limiting, error handling, and response parsing.
    
    Attributes:
        base_url: Base URL for ESPN API endpoints
        request_delay: Delay between requests in seconds for rate limiting
        timeout: Request timeout in seconds
        session: Aiohttp client session for making requests
    """
    
    def __init__(
        self,
        base_url: str = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        request_delay: float = 0.5,
        timeout: int = 30
    ):
        """
        Initialize a new ESPN API client.
        
        Args:
            base_url: Base URL for ESPN API endpoints
            request_delay: Delay between requests in seconds for rate limiting
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.request_delay = request_delay
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0
    
    async def __aenter__(self):
        """Initialize client session on context entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close client session on context exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    @retry(
        max_attempts=3,
        backoff_factor=2.0,
        jitter=0.2,
        exceptions=(
            aiohttp.ClientError,
            asyncio.TimeoutError,
            RateLimitExceededError
        )
    )
    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the ESPN API with rate limiting and retries.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters for the request
            
        Returns:
            Response data as a dictionary
            
        Raises:
            ESPNAPIError: If the API returns an error
            RateLimitExceededError: If the API rate limit is exceeded
        """
        if self._session is None or self._session.closed:
            await self.initialize()
        
        # Apply rate limiting
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"Making request to {url} with params {params}")
        
        try:
            self._last_request_time = asyncio.get_event_loop().time()
            async with self._session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("ESPN API rate limit exceeded")
                    raise RateLimitExceededError("ESPN API rate limit exceeded")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"ESPN API error: {response.status} - {error_text}")
                    err_msg = (
                        f"ESPN API returned status {response.status}: {error_text}"
                    )
                    raise ESPNAPIError(err_msg)
                
                response_data = await response.json()
                return response_data
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Network error during ESPN API request: {str(e)}")
            raise
    
    async def get_season_games(self, season: int) -> List[Dict[str, Any]]:
        """
        Get all games for a specific NCAA basketball season.
        
        Args:
            season: Season year (e.g., 2023 for the 2022-2023 season)
            
        Returns:
            List of games with basic information
        """
        # For ESPN, we need to convert the season year to their format
        # e.g., 2023 season is represented as 2022-23
        season_str = f"{season-1}-{str(season)[-2:]}"
        
        logger.info(f"Retrieving games for season {season_str}")
        
        # This is a simplified implementation - in reality, we would need to 
        # paginate through weeks or make multiple requests
        games = []
        
        # We might need to fetch conference data first
        params = {
            "season": season_str,
            "limit": 100,  # Adjust as needed
            "groups": 50,  # Men's NCAA Basketball group ID
        }
        
        # In a real implementation, we would need to handle pagination
        # and make multiple requests to get all games
        response = await self._make_request("scoreboard", params)
        
        # Process and return the games
        if "events" in response:
            for event in response["events"]:
                home_team = None
                away_team = None
                home_score = None
                away_score = None
                
                # Extract teams and scores
                if "competitions" in event and len(event["competitions"]) > 0:
                    competition = event["competitions"][0]
                    for competitor in competition.get("competitors", []):
                        team_data = {
                            "id": competitor.get("id"),
                            "name": competitor.get("team", {}).get("displayName"),
                            "abbreviation": (
                                competitor.get("team", {}).get("abbreviation")
                            )
                        }
                        
                        if competitor.get("homeAway") == "home":
                            home_team = team_data
                            home_score = int(competitor.get("score", 0))
                        else:
                            away_team = team_data
                            away_score = int(competitor.get("score", 0))
                
                # Create game object
                if home_team and away_team:
                    game = {
                        "id": event.get("id"),
                        "date": event.get("date"),
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": home_score,
                        "away_score": away_score,
                        "status": (event.get("status", {})
                                  .get("type", {})
                                  .get("name", "")
                                  .lower())
                    }
                    games.append(game)
        
        return games
    
    async def get_teams(self, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all NCAA basketball teams.
        
        Args:
            season: Optional season year to filter teams
            
        Returns:
            List of teams with information
        """
        logger.info(f"Retrieving teams{f' for season {season}' if season else ''}")
        
        params = {
            "limit": 500,  # Adjust as needed
            "groups": 50,  # Men's NCAA Basketball group ID
        }
        
        if season:
            season_str = f"{season-1}-{str(season)[-2:]}"
            params["season"] = season_str
        
        response = await self._make_request("teams", params)
        
        teams = []
        if "sports" in response and len(response["sports"]) > 0:
            leagues = response["sports"][0].get("leagues", [])
            if leagues:
                for team in leagues[0].get("teams", []):
                    team_data = team.get("team", {})
                    teams.append({
                        "id": team_data.get("id"),
                        "name": team_data.get("displayName"),
                        "abbreviation": team_data.get("abbreviation"),
                        "conference": {
                            "id": team_data.get("conferenceId"),
                            "name": team_data.get("conference", {}).get("name")
                        }
                    })
        
        return teams
    
    async def get_game_details(self, game_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific game.
        
        Args:
            game_id: ESPN game ID
            
        Returns:
            Detailed game information including venue and statistics
        """
        logger.info(f"Retrieving details for game {game_id}")
        
        response = await self._make_request("summary", {"event": game_id})
        
        game_details = {
            "id": game_id,
        }
        
        # Extract venue information
        if "gameInfo" in response and "venue" in response["gameInfo"]:
            venue = response["gameInfo"]["venue"]
            game_details["venue"] = {
                "id": venue.get("id"),
                "name": venue.get("fullName")
            }
            game_details["attendance"] = response["gameInfo"].get("attendance")
        
        # Extract detailed statistics
        game_details["detailed_stats"] = {}
        
        if "boxscore" in response and "teams" in response["boxscore"]:
            stats = {}
            for team_stats in response["boxscore"]["teams"]:
                is_home = team_stats.get("homeAway") == "home"
                team_key = "home" if is_home else "away"
                
                # Extract statistics for various categories
                for stat in team_stats.get("statistics", []):
                    stat_name = stat.get("name", "").lower().replace(" ", "_")
                    stat_value = stat.get("displayValue")
                    
                    if stat_name not in stats:
                        stats[stat_name] = {}
                    
                    stats[stat_name][team_key] = stat_value
            
            game_details["detailed_stats"] = stats
        
        return game_details 