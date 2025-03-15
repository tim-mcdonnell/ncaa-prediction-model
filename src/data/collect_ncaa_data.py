#!/usr/bin/env python
"""
NCAA Basketball Data Collection Script

This script collects NCAA basketball game data from the ESPN API.
It can be configured to collect data for specific date ranges or seasons.
"""

import argparse
import asyncio
import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import polars as pl
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Base directories
DATA_DIR = "data"
SEASONS_DIR = f"{DATA_DIR}/seasons"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect NCAA basketball data from ESPN API"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2023,
        help="Start year for data collection (default: 2023)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2023,
        help="End year for data collection (default: 2023)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save raw API responses to tmp directory for debugging (default: False)"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Rate limit in seconds between API calls (default: 1.0)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for API calls (default: 3)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Use incremental update (only fetch new data) (default: False)"
    )
    
    return parser.parse_args()


def get_season_date_range(year):
    """Get the date range for a specific NCAA basketball season."""
    # NCAA season typically runs from November to April of the following year
    season_start = f"{year}1101"  # November 1st of the season start year
    season_end = f"{year + 1}0430"  # April 30th of the season end year
    
    return season_start, season_end


async def fetch_scoreboard(client, date_str, retry_count=0, max_retries=3, debug=False):
    """Fetch scoreboard data for a specific date from the ESPN API."""
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    params = {"dates": date_str}
    
    logger.debug(f"Fetching data for date: {date_str}")
    
    try:
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # If debug flag is set, save raw response to tmp directory
            if debug:
                year = date_str[:4]
                debug_dir = Path(tempfile.gettempdir()) / "debug_data" / year
                debug_dir.mkdir(parents=True, exist_ok=True)
                
                debug_file = debug_dir / f"response_{date_str}.json"
                with open(debug_file, "w") as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"Saved debug data to {debug_file}")
            
            return data
        else:
            # Handle errors and retries
            if retry_count < max_retries:
                wait_time = (retry_count + 1) * 2
                logger.warning(
                    f"Error fetching data for {date_str}, "
                    f"status: {response.status_code}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                return await fetch_scoreboard(
                    client, date_str, retry_count + 1, max_retries, debug
                )
            else:
                logger.error(
                    f"Failed to fetch data for {date_str} after {max_retries} retries."
                )
                return {"events": []}
            
    except Exception as e:
        # Handle connection errors
        if retry_count < max_retries:
            wait_time = (retry_count + 1) * 2
            logger.warning(
                f"Error fetching data for {date_str}: {str(e)}. "
                f"Retrying in {wait_time}s..."
            )
            await asyncio.sleep(wait_time)
            return await fetch_scoreboard(
                client, date_str, retry_count + 1, max_retries, debug
            )
        else:
            logger.error(
                f"Failed to fetch data for {date_str} after {max_retries} retries: "
                f"{str(e)}"
            )
            return {"events": []}


async def fetch_game_details(
    client, game_id, retry_count=0, max_retries=3, debug=False
):
    """Fetch detailed information for a specific game from the ESPN API."""
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary"
    params = {"event": game_id}
    
    logger.debug(f"Fetching game details for game ID: {game_id}")
    
    try:
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # If debug flag is set, save raw response to tmp directory
            if debug:
                debug_dir = Path(tempfile.gettempdir()) / "debug_data" / "game_details"
                debug_dir.mkdir(parents=True, exist_ok=True)
                
                debug_file = debug_dir / f"game_{game_id}.json"
                with open(debug_file, "w") as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"Saved debug game details to {debug_file}")
            
            return data
        else:
            # Handle errors and retries
            if retry_count < max_retries:
                wait_time = (retry_count + 1) * 2
                logger.warning(
                    f"Error fetching game details for {game_id}, "
                    f"status: {response.status_code}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                return await fetch_game_details(
                    client, game_id, retry_count + 1, max_retries, debug
                )
            else:
                logger.error(
                    f"Failed to fetch game details for {game_id} "
                    f"after {max_retries} retries."
                )
                return None
            
    except Exception as e:
        # Handle connection errors
        if retry_count < max_retries:
            wait_time = (retry_count + 1) * 2
            logger.warning(
                f"Error fetching game details for {game_id}: {str(e)}. "
                f"Retrying in {wait_time}s..."
            )
            await asyncio.sleep(wait_time)
            return await fetch_game_details(
                client, game_id, retry_count + 1, max_retries, debug
            )
        else:
            logger.error(
                f"Failed to fetch game details for {game_id} after {max_retries} "
                f"retries: {str(e)}"
            )
            return None


def extract_game_data(event):
    """Extract relevant game data from an event object."""
    try:
        competition = event["competitions"][0]
        status = competition["status"]["type"]
        
        # Extract team data
        home_team = None
        away_team = None
        for competitor in competition["competitors"]:
            if competitor["homeAway"] == "home":
                home_team = competitor
            else:
                away_team = competitor
                
        if not home_team or not away_team:
            logger.warning(f"Missing team data for game {event['id']}")
            return None
            
        # Extract scores, handling potential missing or non-numeric values
        try:
            home_score = int(home_team["score"])
        except (KeyError, ValueError, TypeError):
            home_score = None
            
        try:
            away_score = int(away_team["score"])
        except (KeyError, ValueError, TypeError):
            away_score = None
            
        # Basic game data
        game_data = {
            "id": event["id"],
            "date": event["date"],
            "name": event["name"],
            "home_team_id": home_team["id"],
            "home_team_name": home_team["team"]["displayName"],
            "away_team_id": away_team["id"],
            "away_team_name": away_team["team"]["displayName"],
            "home_score": home_score,
            "away_score": away_score,
            "status": status.get("name", "Unknown"),
            "collection_timestamp": datetime.now().timestamp()
        }
        
        # Additional data if available
        if "venue" in competition:
            game_data["venue_name"] = competition["venue"].get("fullName")
            if "address" in competition["venue"]:
                game_data["venue_city"] = competition["venue"]["address"].get("city")
                game_data["venue_state"] = competition["venue"]["address"].get("state")
                
        if "broadcasts" in competition:
            broadcasts = [
                b["names"][0] for b in competition.get("broadcasts", []) 
                if "names" in b and b["names"]
            ]
            game_data["broadcasts"] = ", ".join(broadcasts) if broadcasts else None
            
        if "odds" in competition:
            try:
                game_data["spread"] = competition["odds"][0].get("spread")
                game_data["over_under"] = competition["odds"][0].get("overUnder")
            except (IndexError, KeyError):
                pass
                
        return game_data
    except Exception as e:
        logger.error(f"Error processing event {event.get('id', 'unknown')}: {str(e)}")
        return None


def extract_game_details(game_id, game_data):
    """Extract relevant details from a game summary response."""
    if game_data is None:
        logger.warning(f"No data available for game {game_id}")
        return None
    
    try:
        # Initialize game details with the game ID
        game_details = {
            "id": game_id,
            "collection_timestamp": datetime.now().timestamp()
        }
        
        # Extract venue information
        if "gameInfo" in game_data and "venue" in game_data["gameInfo"]:
            venue = game_data["gameInfo"]["venue"]
            game_details["venue_id"] = venue.get("id", "")
            game_details["venue_name"] = venue.get("fullName", "")
        
        # Extract attendance if available
        if "gameInfo" in game_data and "attendance" in game_data["gameInfo"]:
            game_details["attendance"] = game_data["gameInfo"].get("attendance", 0)
        
        # Extract team statistics
        if "boxscore" in game_data and "teams" in game_data["boxscore"]:
            for team_data in game_data["boxscore"]["teams"]:
                is_home = team_data.get("homeAway") == "home"
                prefix = "home" if is_home else "away"
                
                # Add team ID
                team_id = team_data.get("team", {}).get("id", "")
                game_details[f"{prefix}_team_id"] = team_id
                
                # Process statistics
                if "statistics" in team_data:
                    for stat_group in team_data.get("statistics", []):
                        for stat in stat_group.get("stats", []):
                            name = stat.get("name", "").lower().replace(" ", "_")
                            value_str = stat.get("displayValue", "0")
                            
                            # Convert to appropriate type 
                            # (int, float, or keep as string)
                            try:
                                if "." in value_str:
                                    value = float(value_str)
                                else:
                                    value = int(value_str)
                            except (ValueError, TypeError):
                                value = value_str
                                
                            game_details[f"{prefix}_{name}"] = value
        
        return game_details
    except Exception as e:
        logger.error(f"Error processing game details for {game_id}: {str(e)}")
        return None


async def collect_date_range(
    start_date, end_date, rate_limit=1.0, max_retries=3, debug=False, incremental=False
):
    """Collect data for a range of dates and save to consolidated season files."""
    # Parse start and end dates
    start_date_obj = datetime.strptime(start_date, "%Y%m%d")
    end_date_obj = datetime.strptime(end_date, "%Y%m%d")
    
    # Determine which seasons are included in the date range
    start_season = start_date_obj.year
    if start_date_obj.month < 7:
        start_season -= 1
        
    end_season = end_date_obj.year
    if end_date_obj.month < 7:
        end_season -= 1
    
    # Initialize accumulation dictionaries for each season
    all_games_by_season = {season: [] for season in range(start_season, end_season + 1)}
    all_teams_by_season = {season: {} for season in range(start_season, end_season + 1)}
    all_game_details_by_season = {
        season: [] for season in range(start_season, end_season + 1)
    }
    
    logger.info(
        f"Collecting data from {start_date} to {end_date} "
        f"(seasons: {start_season}-{end_season})"
    )
    
    # Create an async HTTP client
    async with httpx.AsyncClient() as client:
        # Generate list of dates to process
        dates = []
        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str = current_date.strftime("%Y%m%d")
            dates.append(date_str)
            current_date += timedelta(days=1)
        
        # Process each date
        for date_str in tqdm(dates, desc="Collecting data", unit="day"):
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            season = date_obj.year if date_obj.month >= 7 else date_obj.year - 1
            
            # Fetch data for this date
            scoreboard_data = await fetch_scoreboard(
                client, 
                date_str, 
                max_retries=max_retries,
                debug=debug
            )
            
            if scoreboard_data is None:
                logger.warning(f"No data returned for {date_str}, skipping")
                continue
                
            # Process events from this date
            events = scoreboard_data.get("events", [])
            logger.debug(f"Found {len(events)} events for {date_str}")
            
            for event in events:
                game_data = extract_game_data(event)
                if game_data:
                    all_games_by_season[season].append(game_data)
                    
                    # Add to team data
                    for team_id, team_name in [
                        (game_data["home_team_id"], game_data["home_team_name"]),
                        (game_data["away_team_id"], game_data["away_team_name"])
                    ]:
                        if team_id not in all_teams_by_season[season]:
                            all_teams_by_season[season][team_id] = {
                                "id": team_id,
                                "name": team_name,
                                "first_seen": game_data["date"],
                                "collection_timestamp": datetime.now().timestamp()
                            }
                    
                    # Fetch detailed game information
                    game_id = game_data["id"]
                    game_details_data = await fetch_game_details(
                        client,
                        game_id,
                        max_retries=max_retries,
                        debug=debug
                    )
                    
                    if game_details_data:
                        game_details = extract_game_details(game_id, game_details_data)
                        if game_details:
                            all_game_details_by_season[season].append(game_details)
                            logger.debug(f"Collected details for game {game_id}")
                    
                    # Add small delay between detailed requests to avoid rate limiting
                    if rate_limit > 0:
                        await asyncio.sleep(rate_limit / 2)
            
            # Add small delay between date requests if needed
            if rate_limit > 0:
                await asyncio.sleep(rate_limit)
    
    # Save data to season files
    seasons_processed = []
    for season, games in all_games_by_season.items():
        if not games:
            logger.info(f"No games found for season {season}")
            continue
            
        logger.info(f"Processing {len(games)} games for season {season}")
        seasons_processed.append(season)
        
        # Convert to DataFrames
        games_df = pl.DataFrame(games)
        teams_df = pl.DataFrame(list(all_teams_by_season[season].values()))
        
        # Create game_details DataFrame if we have any details
        game_details_df = None
        if all_game_details_by_season[season]:
            game_details_df = pl.DataFrame(all_game_details_by_season[season])
        
        # Prepare season directory
        season_dir = Path(SEASONS_DIR) / str(season)
        season_dir.mkdir(parents=True, exist_ok=True)
        
        games_path = season_dir / "games.parquet"
        teams_path = season_dir / "teams.parquet"
        game_details_path = season_dir / "game_details.parquet"
        
        # Handle incremental updates
        if incremental and games_path.exists():
            logger.info(f"Performing incremental update for season {season}")
            try:
                # Read existing data
                existing_games = pl.read_parquet(games_path)
                
                # Create a set of existing game IDs for faster lookup
                existing_ids = set(existing_games["id"].to_list())
                
                # Separate new and existing games
                new_games = []
                updated_games = []
                
                for game in games:
                    if game["id"] in existing_ids:
                        updated_games.append(game)
                    else:
                        new_games.append(game)
                
                # Process updates and additions
                if updated_games or new_games:
                    # Remove games that will be updated
                    updated_ids = {game["id"] for game in updated_games}
                    filtered_existing = existing_games.filter(
                        ~pl.col("id").is_in(updated_ids)
                    )
                    
                    # Create DataFrames for updated and new games
                    updated_df = pl.DataFrame(updated_games) if updated_games else None
                    new_games_df = pl.DataFrame(new_games) if new_games else None
                    
                    # Combine filtered existing with updated and new games
                    frames_to_concat = [
                        df for df in [filtered_existing, updated_df, new_games_df] 
                        if df is not None and len(df) > 0
                    ]
                    games_df = pl.concat(frames_to_concat)
                    
                    logger.info(
                        f"Updated {len(updated_games)} existing games and "
                        f"added {len(new_games)} new games in season {season}"
                    )
                else:
                    # If no updates or new games, keep existing data
                    games_df = existing_games
                    logger.info(f"No changes to games for season {season}")
                
                # Update teams dataframe if needed
                if teams_path.exists():
                    existing_teams = pl.read_parquet(teams_path)
                    existing_team_ids = set(existing_teams["id"].to_list())
                    
                    new_teams = [
                        team for team_id, team in all_teams_by_season[season].items() 
                        if team_id not in existing_team_ids
                    ]
                    
                    if new_teams:
                        new_teams_df = pl.DataFrame(new_teams)
                        teams_df = pl.concat([existing_teams, new_teams_df])
                        logger.info(
                            f"Added {len(new_teams)} new teams to season {season}"
                        )
                    else:
                        teams_df = existing_teams
                
                # Update game details dataframe if needed
                if game_details_path.exists() and game_details_df is not None:
                    try:
                        existing_details = pl.read_parquet(game_details_path)
                        existing_detail_ids = set(existing_details["id"].to_list())
                        
                        # Process current game details
                        if len(game_details_df) > 0:
                            # Separate new and updated details
                            new_detail_ids = set(game_details_df["id"].to_list())
                            
                            # Filter out existing details that will be updated
                            filtered_existing_details = existing_details.filter(
                                ~pl.col("id").is_in(new_detail_ids)
                            )
                            
                            # Combine with new/updated details
                            game_details_df = pl.concat([
                                filtered_existing_details, game_details_df
                            ])
                            
                            updated_count = len(new_detail_ids & existing_detail_ids)
                            new_count = len(new_detail_ids - existing_detail_ids)
                            logger.info(
                                f"Updated {updated_count} existing game details and "
                                f"added {new_count} new game details"
                            )
                        else:
                            # Keep existing details
                            game_details_df = existing_details
                    except Exception as e:
                        logger.error(
                            f"Error during incremental update for game details: "
                            f"{str(e)}"
                        )
            except Exception as e:
                logger.error(
                    f"Error during incremental update for season {season}: {str(e)}"
                )
                logger.warning(f"Falling back to full replacement for season {season}")
        
        # Write data to parquet files
        logger.info(f"Writing {games_df.shape[0]} games to {games_path}")
        games_df.write_parquet(games_path)
        
        logger.info(f"Writing {teams_df.shape[0]} teams to {teams_path}")  
        teams_df.write_parquet(teams_path)
        
        # Write game details if available
        if game_details_df is not None and len(game_details_df) > 0:
            logger.info(
                f"Writing {game_details_df.shape[0]} game details to "
                f"{game_details_path}"
            )
            game_details_df.write_parquet(game_details_path)
        
        games_count = len(games)
        teams_count = len(all_teams_by_season[season])
        details_count = len(all_game_details_by_season[season])
        logger.info(
            f"Saved data for season {season}: {games_count} games, "
            f"{teams_count} teams, and {details_count} game details"
        )
    
    return seasons_processed


async def collect_seasons(
    start_year, end_year, rate_limit=1.0, max_retries=3, debug=False, incremental=False
):
    """Collect data for multiple seasons."""
    all_seasons = []
    
    for year in range(start_year, end_year + 1):
        logger.info(f"Collecting data for {year}-{year+1} season")
        
        start_date, end_date = get_season_date_range(year)
        
        seasons = await collect_date_range(
            start_date,
            end_date,
            rate_limit=rate_limit,
            max_retries=max_retries,
            debug=debug,
            incremental=incremental
        )
        
        all_seasons.extend(seasons)
    
    return all_seasons


async def main():
    """Main entry point for the script."""
    args = parse_args()
    
    logger.info("Starting NCAA basketball data collection")
    logger.info(f"Years: {args.start_year}-{args.end_year}")
    logger.info(f"Debug mode: {args.debug}")
    logger.info(f"Rate limit: {args.rate_limit}s")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Incremental mode: {args.incremental}")
    
    seasons = await collect_seasons(
        args.start_year,
        args.end_year,
        rate_limit=args.rate_limit,
        max_retries=args.max_retries,
        debug=args.debug,
        incremental=args.incremental
    )
    
    if seasons:
        logger.info(f"Successfully collected data for {len(seasons)} seasons")
    else:
        logger.warning("No data was collected")
    
    logger.info("Data collection complete")


if __name__ == "__main__":
    asyncio.run(main()) 