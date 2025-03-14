"""
Collection Pipeline

This module implements the Collection Pipeline component, which is responsible for
retrieving NCAA basketball data from the ESPN API and storing it in Parquet format,
with support for both complete season collection and incremental updates.
"""

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from src.data.collection.espn.client import ESPNClient
from src.pipelines.base_pipeline import (
    BasePipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
)

# Setup logging
logger = logging.getLogger(__name__)


class CollectionPipeline(BasePipeline):
    """
    Pipeline for collecting NCAA basketball data from ESPN API
    and storing it as Parquet files.
    
    This pipeline handles both full season collection and incremental updates, with
    proper rate limiting and error handling.
    
    Attributes:
        data_dir: Directory where collected data will be stored
        rate_limit: Rate limit for API requests per second
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        rate_limit: float = 5.0,
        burst_limit: int = 10
    ):
        """
        Initialize the collection pipeline.
        
        Args:
            data_dir: Base directory for storing collected data
            rate_limit: Requests per second rate limit for API
            burst_limit: Maximum burst of requests allowed
        """
        super().__init__()
        self.data_dir = data_dir
        self.rate_limit = rate_limit
        self.burst_limit = burst_limit
        self._espn_client: Optional[ESPNClient] = None
    
    async def _validate(self, context: PipelineContext) -> bool:
        """
        Validate the pipeline context.
        
        Args:
            context: Pipeline execution context
            
        Returns:
            True if context is valid, False otherwise
        """
        # Check required parameters
        if "season" not in context.params:
            logger.error("Missing required parameter: season")
            return False
        
        # Validate mode parameter if provided
        mode = context.params.get("mode", "full")
        if mode not in ["full", "incremental"]:
            error_msg = (
                f"Invalid mode parameter: {mode}. Must be 'full' or 'incremental'"
            )
            logger.error(error_msg)
            return False
        
        return True
    
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        """
        Execute the collection pipeline.
        
        This method orchestrates the data collection process, either for a full season
        or as an incremental update, storing the retrieved data in Parquet format.
        
        Args:
            context: Execution context with parameters
            
        Returns:
            Result of the pipeline execution
        """
        season = context.params["season"]
        mode = context.params.get("mode", "full")
        
        logger.info(f"Starting collection for season {season} in {mode} mode")
        
        try:
            # Prepare output directory
            season_dir = Path(self.data_dir) / "seasons" / str(season)
            os.makedirs(season_dir, exist_ok=True)
            
            # Initialize ESPN client
            async with ESPNClient(
                rate_limit=self.rate_limit,
                burst_limit=self.burst_limit
            ) as espn_client:
                # Collect data
                result_data = {}
                
                # 1. Collect games
                games = await self._collect_games(espn_client, season, season_dir, mode)
                result_data["games"] = games
                
                # 2. Collect teams
                teams = await self._collect_teams(espn_client, season, season_dir)
                result_data["teams"] = teams
                
                # 3. Collect game details
                game_details = await self._collect_game_details(
                    espn_client, games, season_dir, mode
                )
                result_data["game_details"] = game_details
                
                # Return success result
                metadata = {
                    "season": season,
                    "mode": mode,
                    "games_count": len(games),
                    "teams_count": len(teams),
                    "details_count": len(game_details),
                    "collection_time": datetime.now().isoformat()
                }
                
                logger.info(
                    f"Collection completed for season {season}: "
                    f"{len(games)} games, {len(teams)} teams"
                )
                
                return PipelineResult(
                    status=PipelineStatus.SUCCESS,
                    output_data=result_data,
                    metadata=metadata
                )
            
        except Exception as e:
            logger.exception(f"Error collecting data for season {season}: {str(e)}")
            error_type = e.__class__.__name__
            return PipelineResult(
                status=PipelineStatus.FAILURE,
                error=e,
                metadata={"season": season, "mode": mode, "error_type": error_type}
            )
    
    async def _collect_games(
        self, 
        espn_client: ESPNClient, 
        season: int,
        season_dir: Path,
        mode: str
    ) -> List[Dict[str, Any]]:
        """
        Collect games for a specified season.
        
        Args:
            espn_client: ESPN API client
            season: Season year
            season_dir: Directory for storing season data
            mode: Collection mode ('full' or 'incremental')
            
        Returns:
            List of collected games
        """
        logger.info(f"Collecting games for season {season}")
        
        # Get existing game data if in incremental mode
        existing_games = {}
        if mode == "incremental" and (season_dir / "games.parquet").exists():
            try:
                existing_df = pl.read_parquet(season_dir / "games.parquet")
                existing_games = {row["id"]: row for row in existing_df.to_dicts()}
                logger.info(
                    f"Found {len(existing_games)} existing games for incremental update"
                )
            except Exception as e:
                logger.warning(
                    "Error reading existing games, falling back to full collection: "
                    f"{str(e)}"
                )
        
        # Calculate date range for the season
        # NCAA basketball season typically runs from November to early April
        season_start = date(season - 1, 11, 1)  # November of the previous year
        season_end = date(season, 4, 15)  # April of the season year
        
        # Fetch games for each date in the season
        all_games = []
        current_date = season_start
        
        while current_date <= season_end:
            date_str = current_date.strftime("%Y%m%d")
            try:
                # Use the ESPNClient's get_scoreboard method
                scoreboard_df = await espn_client.get_scoreboard(date_str)
                
                if not scoreboard_df.is_empty():
                    # Convert DataFrame to list of dictionaries
                    date_games = scoreboard_df.to_dicts()
                    all_games.extend(date_games)
                    logger.debug(f"Retrieved {len(date_games)} games for {date_str}")
                
                # Move to next date
                current_date = current_date + timedelta(days=1)
                
            except Exception as e:
                logger.error(f"Error retrieving games for date {date_str}: {str(e)}")
                # Continue to next date even if there's an error
                current_date = current_date + timedelta(days=1)
        
        logger.info(f"Retrieved {len(all_games)} total games for season {season}")
        
        # Transform games to ensure correct structure if needed
        transformed_games = []
        for game in all_games:
            # Make sure all required fields are present
            transformed_game = {
                "id": game.get("id", ""),
                "date": game.get("date", ""),
                "home_team_id": game.get("home_team_id", ""),
                "away_team_id": game.get("away_team_id", ""),
                "home_score": game.get("home_score", 0),
                "away_score": game.get("away_score", 0),
                "status": game.get("status", ""),
                "collection_timestamp": datetime.now().isoformat()
            }
            transformed_games.append(transformed_game)
        
        # Merge with existing data if in incremental mode
        if mode == "incremental" and existing_games:
            # Create set of processed game IDs
            processed_ids = set()
            
            final_games = []
            # Add all new and updated games
            for game in transformed_games:
                game_id = game["id"]
                processed_ids.add(game_id)
                
                # If game exists and hasn't changed, use existing data
                if game_id in existing_games:
                    existing_game = existing_games[game_id]
                    # Check if any of the important fields changed
                    if (game["home_score"] != existing_game["home_score"] or
                        game["away_score"] != existing_game["away_score"] or
                        game["status"] != existing_game["status"]):
                        # Game updated, use new data
                        final_games.append(game)
                        logger.debug(f"Updated game: {game_id}")
                    else:
                        # Game unchanged, use existing data
                        final_games.append(existing_game)
                else:
                    # New game, add it
                    final_games.append(game)
                    logger.debug(f"New game: {game_id}")
            
            # Add existing games that weren't in the API response
            for game_id, game in existing_games.items():
                if game_id not in processed_ids:
                    final_games.append(game)
            
            transformed_games = final_games
            logger.info(
                f"Merged data: {len(transformed_games)} "
                f"total games after incremental update"
            )
        
        # Convert to Polars DataFrame and save as Parquet
        games_df = pl.DataFrame(transformed_games)
        games_df.write_parquet(season_dir / "games.parquet")
        logger.info(
            f"Saved {len(transformed_games)} games to {season_dir / 'games.parquet'}"
        )
        
        return transformed_games
    
    async def _collect_teams(
        self, 
        espn_client: ESPNClient, 
        season: int,
        season_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Collect teams for a specified season.
        
        Args:
            espn_client: ESPN API client
            season: Season year
            season_dir: Directory for storing season data
            
        Returns:
            List of collected teams
        """
        logger.info(f"Collecting teams for season {season}")
        
        # Fetch teams using the ESPNClient's method for getting teams
        try:
            # Get teams DataFrame
            teams_df = await espn_client.get_teams(season)
            
            # Convert to list of dictionaries
            teams = teams_df.to_dicts()
            
            logger.info(f"Retrieved {len(teams)} teams for season {season}")
            
            # Write teams to Parquet file
            teams_df.write_parquet(season_dir / "teams.parquet")
            logger.info(f"Saved {len(teams)} teams to {season_dir / 'teams.parquet'}")
            
            return teams
            
        except Exception as e:
            logger.error(f"Error retrieving teams for season {season}: {str(e)}")
            # Return empty list on error
            return []
    
    async def _collect_game_details(
        self, 
        espn_client: ESPNClient, 
        games: List[Dict[str, Any]],
        season_dir: Path,
        mode: str
    ) -> List[Dict[str, Any]]:
        """
        Collect detailed information for each game.
        
        Args:
            espn_client: ESPN API client
            games: List of games to collect details for
            season_dir: Directory for storing season data
            mode: Collection mode ('full' or 'incremental')
            
        Returns:
            List of collected game details
        """
        logger.info(f"Collecting details for {len(games)} games")
        
        # Get IDs of games we need to collect details for
        game_ids = [game["id"] for game in games]
        
        # Get existing game details if in incremental mode
        existing_details = {}
        if mode == "incremental" and (season_dir / "game_details.parquet").exists():
            try:
                existing_df = pl.read_parquet(season_dir / "game_details.parquet")
                existing_details = {row["id"]: row for row in existing_df.to_dicts()}
                logger.info(f"Found {len(existing_details)} existing game details")
            except Exception as e:
                logger.warning(
                    "Error reading existing game details, "
                    f"falling back to full collection: {str(e)}"
                )
        
        # For incremental mode, filter to only collect new or updated games
        if mode == "incremental" and existing_details:
            # Filter to games that don't have details or may have updated details
            need_details_ids = []
            for game in games:
                game_id = game["id"]
                
                # Collect details if:
                # 1. We don't have details for this game yet, or
                # 2. The game status is not "final" (may have been updated)
                if (game_id not in existing_details or 
                    game["status"] != "final"):
                    need_details_ids.append(game_id)
            
            game_ids = need_details_ids
            logger.info(f"Filtered to {len(game_ids)} games needing details")
        
        # Collect details for each game
        all_details = []
        for game_id in game_ids:
            try:
                # Use the ESPNClient's method for getting game summary/details
                game_summary = await espn_client.get_game_summary(game_id)
                
                # Create a dictionary with relevant details from the GameSummaryResponse
                details = {
                    "id": game_id,
                    "collection_timestamp": datetime.now().isoformat()
                }
                
                # Extract relevant data from boxscore
                if hasattr(game_summary, "boxscore") and game_summary.boxscore:
                    has_teams = (hasattr(game_summary.boxscore, "teams") and 
                                game_summary.boxscore.teams)
                    if has_teams:
                        for team_data in game_summary.boxscore.teams:
                            # We don't need team_id, so we won't assign it
                            is_home = team_data.get("homeAway", "") == "home"
                            prefix = "home" if is_home else "away"
                            
                            # Add team statistics
                            if "statistics" in team_data:
                                for stat_group in team_data["statistics"]:
                                    for stat in stat_group.get("stats", []):
                                        name = stat.get("name", "").lower()
                                        stat_name = name.replace(" ", "_")
                                        value = stat.get("value", 0)
                                        details[f"{prefix}_{stat_name}"] = value
                
                # Add venue information if available
                if hasattr(game_summary, "game_info") and game_summary.game_info:
                    if "venue" in game_summary.game_info:
                        venue = game_summary.game_info["venue"]
                        details["venue_id"] = venue.get("id", "")
                        details["venue_name"] = venue.get("fullName", "")
                    
                    if "attendance" in game_summary.game_info:
                        attendance = game_summary.game_info.get("attendance", 0)
                        details["attendance"] = attendance
                
                all_details.append(details)
                logger.debug(f"Collected details for game {game_id}")
                
            except Exception as e:
                logger.error(f"Error collecting details for game {game_id}: {str(e)}")
        
        # Merge with existing details if in incremental mode
        if mode == "incremental" and existing_details:
            # Get IDs of games we processed
            processed_ids = {details["id"] for details in all_details}
            
            # Add existing details for games we didn't process
            for game_id, details in existing_details.items():
                if game_id not in processed_ids:
                    all_details.append(details)
            
            logger.info(
                f"Merged data: {len(all_details)} "
                f"total game details after incremental update"
            )
        
        # Convert to Polars DataFrame and save as Parquet
        if all_details:
            details_df = pl.DataFrame(all_details)
            details_df.write_parquet(season_dir / "game_details.parquet")
            logger.info(
                f"Saved {len(all_details)} game details to "
                f"{season_dir / 'game_details.parquet'}"
            )
        else:
            logger.warning("No game details collected")
        
        return all_details
    
    async def collect_season_games(
        self, season: int, mode: str = "full"
    ) -> PipelineResult:
        """
        Collect games for a specific season.
        
        This is a convenience method that wraps the pipeline execution.
        
        Args:
            season: Season year to collect data for
            mode: Collection mode ('full' or 'incremental')
            
        Returns:
            Result of the collection operation
        """
        context = PipelineContext(params={"season": season, "mode": mode})
        return await self.execute(context)
    
    async def collect_all_seasons(
        self, start_year: int, end_year: Optional[int] = None
    ) -> List[PipelineResult]:
        """
        Collect games for multiple seasons.
        
        Args:
            start_year: First season year to collect
            end_year: Last season year to collect (defaults to current year)
            
        Returns:
            List of results for each season
        """
        if end_year is None:
            # Default to current year
            end_year = datetime.now().year
        
        results = []
        for year in range(start_year, end_year + 1):
            result = await self.collect_season_games(year)
            results.append(result)
        
        return results
    
    async def _cleanup(self) -> None:
        """Clean up resources used by the pipeline."""
        # The ESPNClient is now managed with async context manager
        # so we don't need to do any cleanup here
        pass
