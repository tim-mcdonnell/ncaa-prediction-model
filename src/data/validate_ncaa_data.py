#!/usr/bin/env python
"""
NCAA Basketball Data Validation

This script performs basic validation and generates a quality report
for collected NCAA basketball data.
"""

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
INPUT_FILE = "data/targeted_collection/all_games.parquet"
OUTPUT_DIR = "data/targeted_collection/validated"


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
    empty_counts = {}
    for col in ["name", "home_team_name", "away_team_name", "status"]:
        if col in df.columns:
            empty_count = df.filter(pl.col(col) == "").height
            if empty_count > 0:
                empty_counts[col] = empty_count
    
    # Prepare validation report
    validation_report = {
        "total_records": df.height,
        "missing_columns": missing_columns,
        "null_counts": null_counts,
        "empty_counts": empty_counts,
        "invalid_scores": {
            "home_score": invalid_home_scores,
            "away_score": invalid_away_scores
        },
        "is_valid": (
            len(missing_columns) == 0 and
            sum(null_counts.values()) == 0 and
            invalid_home_scores == 0 and
            invalid_away_scores == 0
        )
    }
    
    return validation_report


def generate_quality_report(df):
    """Generate a quality report for the data."""
    # Basic statistics
    total_games = df.height
    unique_teams = len(
        set(df["home_team_id"].to_list() + df["away_team_id"].to_list())
    )
    
    # Date range
    min_date = df["date"].min()
    max_date = df["date"].max()
    
    # Score statistics
    avg_home_score = df["home_score"].mean()
    avg_away_score = df["away_score"].mean()
    max_score = max(df["home_score"].max(), df["away_score"].max())
    min_score = min(df["home_score"].min(), df["away_score"].min())
    
    # Game status
    status_counts = df.group_by("status").agg(pl.len()).sort("len", descending=True)
    status_dict = {row["status"]: row["len"] for row in status_counts.to_dicts()}
    
    # Column statistics
    column_stats = []
    for col in df.columns:
        col_type = str(df[col].dtype)
        null_count = df.filter(pl.col(col).is_null()).height
        unique_count = df[col].n_unique()
        
        col_stat = {
            "column": col,
            "dtype": col_type,
            "null_count": null_count,
            "unique_count": unique_count
        }
        
        # Add numeric stats for numeric columns
        if col in ["home_score", "away_score"]:
            col_stat.update({
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median())
            })
        
        column_stats.append(col_stat)
    
    # Prepare quality report
    quality_report = {
        "overall_stats": {
            "total_games": total_games,
            "unique_teams": unique_teams,
            "date_range": f"{min_date} to {max_date}",
            "score_range": f"{min_score} to {max_score}",
            "avg_home_score": float(avg_home_score),
            "avg_away_score": float(avg_away_score)
        },
        "status_counts": status_dict,
        "column_stats": column_stats
    }
    
    return quality_report


def main():
    """Main function to validate collected data."""
    logger.info("Starting data validation")
    
    # Create output directory
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load collected data
    logger.info(f"Loading data from {INPUT_FILE}")
    df = pl.read_parquet(INPUT_FILE)
    logger.info(f"Loaded {len(df)} games")
    
    # 1. Validate data
    logger.info("Validating data")
    validation_report = validate_data(df)
    
    # Save validation report
    validation_report_path = output_dir / "validation_report.json"
    with open(validation_report_path, "w") as f:
        json.dump(validation_report, f, indent=2)
    
    logger.info(f"Validation result: {validation_report['is_valid']}")
    
    # 2. Generate quality report
    logger.info("Generating quality report")
    quality_report = generate_quality_report(df)
    
    # Save quality report
    quality_report_path = output_dir / "quality_report.json"
    with open(quality_report_path, "w") as f:
        json.dump(quality_report, f, indent=2)
    
    # 3. Save cleaned data (just a copy for now)
    logger.info("Saving cleaned data")
    cleaned_file = output_dir / "cleaned_games.parquet"
    df.write_parquet(cleaned_file)
    
    # 4. Print summary
    print("\nData Validation Summary:")
    print(f"Total games: {df.height}")
    print(f"Valid: {validation_report['is_valid']}")
    
    if validation_report["missing_columns"]:
        print(f"Missing columns: {validation_report['missing_columns']}")
    
    if validation_report["null_counts"]:
        print("\nNull values:")
        for col, count in validation_report["null_counts"].items():
            print(f"- {col}: {count} nulls")
    
    if validation_report["empty_counts"]:
        print("\nEmpty strings:")
        for col, count in validation_report["empty_counts"].items():
            print(f"- {col}: {count} empty values")
    
    print("\nData Quality Summary:")
    print(f"Date range: {quality_report['overall_stats']['date_range']}")
    print(f"Unique teams: {quality_report['overall_stats']['unique_teams']}")
    print(f"Score range: {quality_report['overall_stats']['score_range']}")
    print(f"Average scores: Home {quality_report['overall_stats']['avg_home_score']:.1f}, " +
          f"Away {quality_report['overall_stats']['avg_away_score']:.1f}")
    
    print("\nGame statuses:")
    for status, count in quality_report["status_counts"].items():
        print(f"- {status}: {count} games")
    
    print(f"\nValidation reports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main() 