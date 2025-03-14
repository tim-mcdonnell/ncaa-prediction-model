# Collecting NCAA Basketball Data

## Goal
This guide shows you how to use the Collection Pipeline to retrieve and store NCAA basketball data from ESPN APIs for further analysis and model training.

## Prerequisites
- Python 3.10+
- Project environment set up (see [Development Setup](../development/setup.md))
- Understanding of NCAA basketball seasons and data structure
- Access to ESPN APIs (no authentication required, but rate limits apply)

## Steps

### 1. Basic Season Collection

To collect data for a complete NCAA basketball season:

```python
import asyncio
from src.pipelines.collection_pipeline import CollectionPipeline

async def collect_data():
    # Initialize the pipeline with default settings
    pipeline = CollectionPipeline(data_dir="data")
    
    # Collect the 2022-23 season (specified as 2023)
    result = await pipeline.collect_season_games(season=2023, mode="full")
    
    print(f"Collection complete - Status: {result.status}")
    print(f"Collected {result.metadata['games_count']} games")
    print(f"Collected {result.metadata['teams_count']} teams")

# Run the async function
asyncio.run(collect_data())
```

This will:
1. Create the directory structure for storing the data
2. Collect all games from the 2022-23 NCAA basketball season
3. Collect team information for all teams in the season
4. Collect detailed statistics for each game
5. Save all data as Parquet files in `data/seasons/2023/`

### 2. Incremental Updates

For regular updates during an active season, use incremental mode:

```python
# Initialize the pipeline
pipeline = CollectionPipeline()

# Run daily in incremental mode
async def update_current_season():
    result = await pipeline.collect_season_games(
        season=2023,
        mode="incremental"
    )
    return result

# Run this function on a daily schedule
```

Incremental collection:
- Reads existing Parquet files
- Only collects new games or games with updated information
- Preserves existing data for unchanged games
- Is significantly faster than full collection for regular updates

### 3. Collecting Multiple Seasons

To collect data for a range of seasons:

```python
async def collect_historical_data():
    pipeline = CollectionPipeline()
    results = await pipeline.collect_all_seasons(
        start_year=2018,
        end_year=2023
    )
    
    # Check results for each season
    for i, result in enumerate(results):
        season = 2018 + i
        print(f"Season {season}: {result.status}")

# Run the async function
asyncio.run(collect_historical_data())
```

### 4. Customizing Rate Limits

To respect ESPN API limits or adjust collection speed:

```python
# More conservative rate limiting for production use
pipeline = CollectionPipeline(
    rate_limit=2.0,     # 2 requests per second
    burst_limit=5       # Allow bursts of up to 5 requests
)
```

### 5. Accessing Collected Data

The collected data is stored in Parquet format and can be loaded using Polars:

```python
import polars as pl

# Load collected data
season_dir = "data/seasons/2023"
games_df = pl.read_parquet(f"{season_dir}/games.parquet")
teams_df = pl.read_parquet(f"{season_dir}/teams.parquet")
details_df = pl.read_parquet(f"{season_dir}/game_details.parquet")

# Display basic statistics
print(f"Total games: {len(games_df)}")
print(f"Total teams: {len(teams_df)}")

# Join data for analysis
games_with_teams = games_df.join(
    teams_df.select("id", "name").rename({"id": "home_team_id", "name": "home_team_name"}),
    on="home_team_id"
).join(
    teams_df.select("id", "name").rename({"id": "away_team_id", "name": "away_team_name"}),
    on="away_team_id"
)

# Show sample of collected data
print(games_with_teams.head(5))
```

## Example
Here's a complete example of a data collection script that might run on a daily schedule:

```python
#!/usr/bin/env python
"""
NCAA Basketball Data Collection Script

This script collects NCAA basketball data incrementally and logs the results.
It's designed to be run on a daily schedule during the basketball season.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.pipelines.collection_pipeline import CollectionPipeline, PipelineStatus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("collection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("collection_script")

async def main():
    # Get current NCAA season (academic year ending)
    current_month = datetime.now().month
    current_year = datetime.now().year
    season_year = current_year if current_month >= 7 else current_year - 1
    
    logger.info(f"Starting incremental data collection for {season_year-1}-{season_year} season")
    
    # Initialize pipeline
    pipeline = CollectionPipeline(
        data_dir="data",
        rate_limit=3.0,  # Conservative rate limit
    )
    
    # Run collection
    result = await pipeline.collect_season_games(
        season=season_year,
        mode="incremental"
    )
    
    # Log results
    if result.status == PipelineStatus.SUCCESS:
        logger.info(
            f"Collection completed successfully: "
            f"{result.metadata['games_count']} games, "
            f"{result.metadata['teams_count']} teams, "
            f"{result.metadata['details_count']} game details"
        )
    else:
        logger.error(f"Collection failed: {result.error}")
    
    return result.status

if __name__ == "__main__":
    exit_code = 0 if asyncio.run(main()) == PipelineStatus.SUCCESS else 1
    exit(exit_code)
```

## Troubleshooting

### Rate Limiting Issues
- **Symptoms**: Collection fails with HTTP 429 errors
- **Solution**: Decrease the `rate_limit` parameter when initializing the pipeline
- **Example**: `pipeline = CollectionPipeline(rate_limit=1.0)`

### Missing or Incomplete Data
- **Symptoms**: Some games or statistics are missing
- **Solution**: 
  1. Check if you're using the correct season year (e.g., 2023 for the 2022-23 season)
  2. Ensure ESPN had coverage for the missing games
  3. Try running in `full` mode to collect all available data

### Season Year Confusion
- **Symptoms**: Data is collected for the wrong season
- **Solution**: Remember that NCAA basketball seasons span two calendar years, and the convention is to use the ending year. For example, the 2022-23 season is specified as season=2023.

### Disk Space Issues
- **Symptoms**: Collection fails with disk-related errors
- **Solution**: Full collection of all NCAA data typically requires at least 2GB of free space. Ensure sufficient disk space is available. 