#!/usr/bin/env python
"""
NCAA Basketball Data Validation

This script performs basic validation and generates a quality report
for collected NCAA basketball data.
"""

import argparse
import json
import logging
from pathlib import Path

import polars as pl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Define input/output paths
DATA_DIR = "data"
SEASONS_DIR = f"{DATA_DIR}/seasons"
OUTPUT_DIR = f"{DATA_DIR}/validated"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate NCAA basketball data")
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Specific season to validate (e.g., 2023 for 2023-24 season)"
    )
    parser.add_argument(
        "--output",
        action="store_true",
        help="Save validation report to output directory"
    )
    
    return parser.parse_args()


def validate_data(df):
    """Perform basic validation on the data."""
    # Check for required columns
    required_columns = [
        "id", "date", "name", "home_team_id", "home_team_name",
        "away_team_id", "away_team_name", "home_score", "away_score",
        "status", "collection_timestamp"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    # Check for null values
    null_counts = {}
    for col in df.columns:
        null_count = df.filter(pl.col(col).is_null()).height
        if null_count > 0:
            null_counts[col] = null_count
    
    # Check for invalid scores (negative)
    invalid_home_scores = df.filter(pl.col("home_score") < 0).height
    invalid_away_scores = df.filter(pl.col("away_score") < 0).height
    
    # Check for empty strings in text fields
    empty_strings = {}
    for col in df.select(pl.col(pl.Utf8)).columns:
        empty_count = df.filter(pl.col(col) == "").height
        if empty_count > 0:
            empty_strings[col] = empty_count
    
    # Check for duplicate game IDs
    total_rows = df.height
    unique_ids = df.select("id").unique().height
    duplicate_count = total_rows - unique_ids
    
    # Check for data completeness
    completed_games = df.filter(pl.col("status") == "STATUS_FINAL").height
    incomplete_games = total_rows - completed_games
    
    # Validation results
    validation_results = {
        "total_games": total_rows,
        "missing_columns": missing_columns,
        "null_values": null_counts,
        "invalid_scores": {
            "home_score_negative": invalid_home_scores,
            "away_score_negative": invalid_away_scores
        },
        "empty_strings": empty_strings,
        "duplicate_ids": duplicate_count,
        "game_status": {
            "completed": completed_games,
            "incomplete": incomplete_games
        }
    }
    
    return validation_results


def generate_quality_report(df):
    """Generate a data quality report for the games data."""
    # Get basic statistics
    total_games = df.height
    
    # Calculate date range
    if "date" in df.columns:
        date_col = df.select("date").to_series()
        date_strings = [str(d).split("T")[0] for d in date_col]
        earliest_date = min(date_strings)
        latest_date = max(date_strings)
    else:
        earliest_date = "unknown"
        latest_date = "unknown"
    
    # Count unique teams
    if all(col in df.columns for col in ["home_team_id", "away_team_id"]):
        home_teams = set(df["home_team_id"].to_list())
        away_teams = set(df["away_team_id"].to_list())
        unique_teams = len(home_teams.union(away_teams))
        teams_as_home = len(home_teams)
        teams_as_away = len(away_teams)
        teams_both = len(home_teams.intersection(away_teams))
    else:
        unique_teams = "unknown"
        teams_as_home = "unknown"
        teams_as_away = "unknown"
        teams_both = "unknown"
    
    # Calculate scoring statistics
    score_stats = {}
    if "home_score" in df.columns and "away_score" in df.columns:
        home_scores = df.select("home_score").to_series()
        away_scores = df.select("away_score").to_series()
        
        # Calculate point differentials for completed games
        completed = df.filter(pl.col("status") == "STATUS_FINAL")
        if completed.height > 0:
            differentials = abs(completed["home_score"] - completed["away_score"])
            score_stats = {
                "avg_home_score": round(float(home_scores.mean()), 2),
                "avg_away_score": round(float(away_scores.mean()), 2),
                "max_home_score": int(home_scores.max()),
                "max_away_score": int(away_scores.max()),
                "min_home_score": int(home_scores.min()),
                "min_away_score": int(away_scores.min()),
                "avg_point_differential": round(float(differentials.mean()), 2),
                "max_point_differential": int(differentials.max())
            }
    
    # Generate the report
    report = {
        "basic_stats": {
            "total_games": total_games,
            "date_range": f"{earliest_date} to {latest_date}",
            "unique_teams": unique_teams,
            "teams_as_home": teams_as_home,
            "teams_as_away": teams_as_away,
            "teams_both_home_and_away": teams_both,
        },
        "score_stats": score_stats,
        "validation": validate_data(df)
    }
    
    return report


def validate_season_data(season):
    """Validate data for a specific season."""
    # Check if season data exists
    season_dir = Path(SEASONS_DIR) / str(season)
    games_path = season_dir / "games.parquet"
    teams_path = season_dir / "teams.parquet"
    game_details_path = season_dir / "game_details.parquet"
    
    if not games_path.exists():
        logger.error(f"Games data not found for season {season}")
        return None
    
    # Load and validate games data
    logger.info(f"Validating games data for season {season}")
    games_df = pl.read_parquet(games_path)
    
    games_report = generate_quality_report(games_df)
    games_report["file_path"] = str(games_path)
    games_report["season"] = season
    
    # Add teams data validation if available
    if teams_path.exists():
        logger.info(f"Validating teams data for season {season}")
        teams_df = pl.read_parquet(teams_path)
        
        teams_report = {
            "total_teams": teams_df.height,
            "file_path": str(teams_path)
        }
        games_report["teams_data"] = teams_report
    
    # Add game details data validation if available
    if game_details_path.exists():
        logger.info(f"Validating game details data for season {season}")
        details_df = pl.read_parquet(game_details_path)
        
        details_report = {
            "total_game_details": details_df.height,
            "columns": details_df.columns,
            "file_path": str(game_details_path)
        }
        
        # Check if we have shooting statistics
        shooting_cols = [
            col for col in details_df.columns 
            if 'fg' in col.lower() or 'ft' in col.lower()
        ]
        if shooting_cols:
            details_report["has_shooting_stats"] = True
            details_report["shooting_columns"] = shooting_cols
        
        games_report["game_details_data"] = details_report
    
    return games_report


def main():
    """Main function to validate NCAA basketball data."""
    args = parse_args()
    
    # Ensure output directory exists if needed
    if args.output:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    if args.season:
        # Validate specific season
        logger.info(f"Validating data for season {args.season}")
        report = validate_season_data(args.season)
        
        # Save or display report
        if args.output and report:
            output_file = Path(OUTPUT_DIR) / (
                f"validation_report_season_{args.season}.json"
            )
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Saved validation report to {output_file}")
    else:
        # Validate all available seasons
        logger.info("Validating data for all available seasons")
        
        # Find all season directories
        season_dirs = list(Path(SEASONS_DIR).glob("*"))
        
        if not season_dirs:
            logger.error(f"No season data found in {SEASONS_DIR}")
            return
        
        # Validate each season
        all_reports = {}
        for season_dir in season_dirs:
            if not season_dir.is_dir():
                continue
                
            season = season_dir.name
            logger.info(f"Processing season {season}")
            
            report = validate_season_data(season)
            if report:
                all_reports[season] = report
        
        # Save combined report if requested
        if args.output and all_reports:
            output_file = Path(OUTPUT_DIR) / "validation_report_all_seasons.json"
            with open(output_file, "w") as f:
                json.dump(all_reports, f, indent=2)
            logger.info(f"Saved validation report for all seasons to {output_file}")
            
            # Print summary
            print("\nValidation Summary:")
            for season, report in all_reports.items():
                total_games = report["basic_stats"]["total_games"]
                validation = report["validation"]
                
                # Check for serious issues
                issues = len(validation["missing_columns"])
                issues += sum(validation["null_values"].values())
                issues += sum(validation["invalid_scores"].values())
                
                status = "🟢 Good" 
                if issues > 0:
                    status = "🟠 Issues Found" if issues < 10 else "🔴 Serious Issues"
                
                print(f"Season {season}: {status} ({total_games} games)")


if __name__ == "__main__":
    main() 