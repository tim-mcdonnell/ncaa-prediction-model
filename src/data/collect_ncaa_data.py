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
import os
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
RAW_DATA_DIR = f"{DATA_DIR}/raw"
PROCESSED_DATA_DIR = f"{DATA_DIR}/targeted_collection"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Collect NCAA basketball data from ESPN API")
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
        "--save-raw",
        action="store_true",
        help="Save raw API responses (default: False)"
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
    
    return parser.parse_args()


def get_season_date_range(year):
    """Get the date range for a specific NCAA basketball season."""
    # NCAA season typically runs from November to April of the following year
    season_start = f"{year}1101"  # November 1st of the season start year
    season_end = f"{year + 1}0430"  # April 30th of the season end year
    
    return season_start, season_end


async def fetch_scoreboard(client, date_str, save_raw=False, retry_count=0, max_retries=3):
    """Fetch scoreboard data for a specific date from the ESPN API."""
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    params = {"dates": date_str}
    
    logger.debug(f"Fetching data for date: {date_str}")
    
    try:
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Optionally save raw response
            if save_raw:
                raw_dir = Path(RAW_DATA_DIR) / date_str[:4]
                raw_dir.mkdir(parents=True, exist_ok=True)
                
                raw_file = raw_dir / f"response_{date_str}.json"
                with open(raw_file, "w") as f:
                    json.dump(data, f, indent=2)
            
            return data
        elif response.status_code >= 500 and retry_count < max_retries:
            # Retry on server errors
            logger.warning(f"Server error {response.status_code} for {date_str}, retrying ({retry_count + 1}/{max_retries})")
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            return await fetch_scoreboard(client, date_str, save_raw, retry_count + 1, max_retries)
        else:
            logger.error(f"Error fetching data: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        if retry_count < max_retries:
            logger.warning(f"Exception fetching data for {date_str}, retrying ({retry_count + 1}/{max_retries}): {str(e)}")
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            return await fetch_scoreboard(client, date_str, save_raw, retry_count + 1, max_retries)
        else:
            logger.exception(f"Exception fetching data after {max_retries} retries: {str(e)}")
            return None


def extract_game_data(event):
    """Extract game data from an event in the ESPN API response."""
    # Check for competitions
    competitions = event.get("competitions", [])
    if not competitions:
        return None
    
    competition = competitions[0]
    
    # Extract game ID (use event ID as the primary source)
    game_id = event.get("id", "")
    if not game_id:
        # Fallback to competition ID if event ID is missing
        game_id = competition.get("id", "")
    
    if not game_id:
        logger.warning(f"No game ID found for event: {event.get('name', 'Unknown')}")
        return None
    
    # Extract status
    status = competition.get("status", {}).get("type", {}).get("name", "UNKNOWN")
    
    # Extract teams and scores
    teams = {}
    for competitor in competition.get("competitors", []):
        home_away = competitor.get("homeAway", "")
        if not home_away:
            continue
        
        team_id = competitor.get("team", {}).get("id", "")
        team_name = competitor.get("team", {}).get("displayName", "")
        
        # Score extraction with proper error handling
        try:
            score_raw = competitor.get("score", "0")
            score = int(score_raw) if score_raw else 0
        except (ValueError, TypeError):
            logger.warning(f"Invalid score format for {team_name}: {score_raw}")
            score = 0
        
        teams[home_away] = {
            "id": team_id,
            "name": team_name,
            "score": score
        }
    
    # Skip games with missing team data
    if "home" not in teams or "away" not in teams:
        logger.warning(f"Missing home or away team data for game {game_id}")
        return None
    
    # Get the date from the event or competition
    date = event.get("date", "") or competition.get("date", "")
    
    # Format date as YYYYMMDD if it's in ISO format
    if date and "T" in date:
        try:
            date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
            date = date_obj.strftime("%Y%m%d")
        except (ValueError, TypeError):
            # Keep original date string if parsing fails
            pass
    
    # Create game record
    game = {
        "id": game_id,
        "date": date,
        "name": event.get("name", ""),
        "home_team_id": teams["home"]["id"],
        "home_team_name": teams["home"]["name"],
        "away_team_id": teams["away"]["id"],
        "away_team_name": teams["away"]["name"],
        "home_score": teams["home"]["score"],
        "away_score": teams["away"]["score"],
        "status": status,
        "collection_timestamp": datetime.now().isoformat()
    }
    
    return game


async def collect_date_range(start_date, end_date, save_raw=False, rate_limit=1.0, max_retries=3):
    """Collect data for a specified date range."""
    # Create output directories
    output_dir = Path(PROCESSED_DATA_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    
    # Calculate number of days
    num_days = (end_dt - start_dt).days + 1
    
    logger.info(f"Collecting data for {num_days} days from {start_date} to {end_date}")
    
    # Create progress bar
    progress = tqdm(total=num_days, desc="Collecting Data", unit="day")
    
    all_games = []
    dates_processed = 0
    
    # Create client with appropriate timeout
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Iterate through each date in the range
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y%m%d")
            
            try:
                # Fetch data for this date
                data = await fetch_scoreboard(client, date_str, save_raw, max_retries=max_retries)
                
                if data:
                    events = data.get("events", [])
                    logger.debug(f"Found {len(events)} events for {date_str}")
                    
                    games_for_date = []
                    for event in events:
                        game = extract_game_data(event)
                        if game:
                            games_for_date.append(game)
                    
                    # Save data for individual date
                    if games_for_date:
                        # Convert to DataFrame and save
                        df = pl.DataFrame(games_for_date)
                        date_file = output_dir / f"games_{date_str}.parquet"
                        df.write_parquet(date_file)
                        logger.debug(f"Saved {len(games_for_date)} games to {date_file}")
                        
                        # Add to overall collection
                        all_games.extend(games_for_date)
                
                # Update progress
                dates_processed += 1
                progress.update(1)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(rate_limit)
                
            except Exception as e:
                logger.error(f"Error processing date {date_str}: {str(e)}")
            
            # Move to next date
            current_dt += timedelta(days=1)
    
    # Close progress bar
    progress.close()
    
    # Save combined data if we have any games
    if all_games:
        combined_df = pl.DataFrame(all_games)
        combined_file = output_dir / "all_games.parquet"
        combined_df.write_parquet(combined_file)
        
        # Also save as JSON for easy inspection
        json_file = output_dir / "all_games.json"
        with open(json_file, "w") as f:
            json.dump(all_games, f, indent=2)
        
        logger.info(f"Saved {len(all_games)} total games to {combined_file} and {json_file}")
        
        # Generate simple summary
        summary = {
            "total_games": len(all_games),
            "date_range": f"{start_date} to {end_date}",
            "dates_with_games": len(set(game["date"] for game in all_games)),
            "dates_processed": dates_processed,
            "unique_teams": len(set([game["home_team_id"] for game in all_games] + 
                                  [game["away_team_id"] for game in all_games])),
            "completed_games": sum(1 for game in all_games if game["status"] == "STATUS_FINAL"),
            "collection_timestamp": datetime.now().isoformat()
        }
        
        # Save summary
        summary_file = output_dir / "collection_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    return {
        "total_games": 0,
        "date_range": f"{start_date} to {end_date}",
        "dates_processed": dates_processed,
        "error": "No games collected"
    }


async def collect_seasons(start_year, end_year, save_raw=False, rate_limit=1.0, max_retries=3):
    """Collect data for multiple NCAA basketball seasons."""
    overall_summary = {
        "seasons": [],
        "total_games": 0,
        "start_time": datetime.now().isoformat()
    }
    
    for year in range(start_year, end_year + 1):
        logger.info(f"Collecting data for {year}-{year+1} season")
        
        # Get date range for this season
        season_start, season_end = get_season_date_range(year)
        
        # Collect data for this season
        season_summary = await collect_date_range(
            season_start, 
            season_end,
            save_raw=save_raw,
            rate_limit=rate_limit,
            max_retries=max_retries
        )
        
        # Add to overall summary
        season_summary["season"] = f"{year}-{year+1}"
        overall_summary["seasons"].append(season_summary)
        overall_summary["total_games"] += season_summary.get("total_games", 0)
    
    # Add end time and duration
    overall_summary["end_time"] = datetime.now().isoformat()
    overall_summary["duration_seconds"] = (
        datetime.fromisoformat(overall_summary["end_time"]) - 
        datetime.fromisoformat(overall_summary["start_time"])
    ).total_seconds()
    
    # Save overall summary
    summary_file = Path(PROCESSED_DATA_DIR) / "overall_collection_summary.json"
    with open(summary_file, "w") as f:
        json.dump(overall_summary, f, indent=2)
    
    return overall_summary


async def main():
    """Main entry point for the script."""
    args = parse_args()
    
    logger.info("Starting NCAA basketball data collection")
    logger.info(f"Collecting seasons from {args.start_year} to {args.end_year}")
    
    try:
        # Create directories
        Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(PROCESSED_DATA_DIR).mkdir(parents=True, exist_ok=True)
        
        # Collect data for specified seasons
        summary = await collect_seasons(
            args.start_year,
            args.end_year,
            save_raw=args.save_raw,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries
        )
        
        logger.info("Collection completed successfully")
        logger.info(f"Collected {summary['total_games']} games across {len(summary['seasons'])} seasons")
        
        # Print summary of findings
        print("\nCollection Summary:")
        print(f"Seasons: {args.start_year}-{args.end_year + 1}")
        print(f"Total Games: {summary['total_games']}")
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Data stored in: {PROCESSED_DATA_DIR}")
        
        for season in summary["seasons"]:
            print(f"\nSeason {season['season']}:")
            print(f"  Games: {season.get('total_games', 0)}")
            print(f"  Dates with games: {season.get('dates_with_games', 0)}")
            print(f"  Completed games: {season.get('completed_games', 0)}")
        
    except Exception as e:
        logger.exception(f"Error in collection process: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 