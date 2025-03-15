# Data Collection

## Overview
The data collection component retrieves NCAA basketball data from ESPN APIs
and stores it in Parquet format for further processing. It supports both full season
collection and incremental updates, with configurable rate limiting to respect ESPN's API constraints.
The data is consolidated into season-based files to improve storage efficiency and access performance.

## Responsibilities
- Fetch game data, team information, and game details from ESPN endpoints
- Handle rate limiting and retries for API requests
- Process and transform API responses to standardized DataFrame format
- Store organized data in consolidated season-based Parquet files
- Support incremental updates to efficiently collect only new or changed data
- Provide debug mode for storing raw API responses for troubleshooting
- Provide comprehensive error handling and logging

## Key Classes and Functions
- `ESPNClient`: Handles API communication with ESPN, including endpoints for scoreboard, team, and game summary data
- `collect_date_range`: Collects data for a range of dates and consolidates it into season files
- `collect_seasons`: Orchestrates data collection for multiple seasons
- `fetch_scoreboard`: Fetches and optionally stores raw API responses when in debug mode
- `extract_game_data`: Transforms API responses into structured game data

## Usage Examples

### Collecting Season Data

```python
# Collect data for a specific season range
import asyncio
from src.data.collect_ncaa_data import collect_seasons

# Collect the 2022-23 season
seasons = asyncio.run(collect_seasons(
    start_year=2022,
    end_year=2022,
    rate_limit=1.0,
    max_retries=3,
    debug=False,
    incremental=False
))

# Incremental update for the current season
seasons = asyncio.run(collect_seasons(
    start_year=2023,
    end_year=2023,
    rate_limit=1.0,
    max_retries=3,
    debug=False,
    incremental=True
))
```

### Command Line Usage

```bash
# Collect a specific season
python -m src.data.collect_ncaa_data --start-year=2022 --end-year=2022

# Collect with debug mode enabled (saves raw responses to tmp directory)
python -m src.data.collect_ncaa_data --start-year=2023 --end-year=2023 --debug

# Perform incremental update of the current season
python -m src.data.collect_ncaa_data --start-year=2023 --end-year=2023 --incremental
```

### Accessing the Collected Data

```python
# Reading the consolidated season data
import polars as pl
from pathlib import Path

# Load games for a specific season
season = 2023
games_df = pl.read_parquet(f"data/seasons/{season}/games.parquet")

# Load team data for a specific season
teams_df = pl.read_parquet(f"data/seasons/{season}/teams.parquet")

# Load game details for a specific season
details_df = pl.read_parquet(f"data/seasons/{season}/game_details.parquet")

# Filter games for a specific team
team_id = "120"  # Example team ID
team_games = games_df.filter(
    (pl.col("home_team_id") == team_id) | 
    (pl.col("away_team_id") == team_id)
)

# Get games within a date range
start_date = "2023-01-01"
end_date = "2023-01-31"
date_filtered_games = games_df.filter(
    (pl.col("date") >= start_date) & 
    (pl.col("date") <= end_date)
)

# Join games with their detailed statistics
games_with_details = games_df.join(
    details_df,
    on="id",
    how="left"
)

# Analyze shooting percentages for home teams
shooting_stats = details_df.select([
    "id",
    "home_team_id",
    "home_field_goal_pct",
    "home_three_point_pct",
    "home_free_throw_pct"
])

# Get average statistics for a team's home games
team_home_stats = details_df.filter(
    pl.col("home_team_id") == team_id
).select([
    pl.mean("home_field_goal_pct").alias("avg_fg_pct"),
    pl.mean("home_three_point_pct").alias("avg_3pt_pct"),
    pl.mean("home_free_throw_pct").alias("avg_ft_pct"),
    pl.mean("home_rebounds").alias("avg_rebounds"),
    pl.mean("home_assists").alias("avg_assists")
])
```

## Data Flow
1. Command line arguments are parsed to determine collection parameters
2. For each date in the specified range, scoreboard data is fetched from ESPN
3. Game and team data is extracted and accumulated in memory by season
4. If debug mode is enabled, raw API responses are saved to the temp directory
5. After all dates are processed, consolidated data is written to season-based files
6. For incremental updates, existing data is merged with new data, updating changed games

## Data Storage Structure
The collection pipeline organizes data in the following structure:

```
data/
└── seasons/
    └── {season}/           # E.g., 2023 for 2022-23 season
        ├── games.parquet   # All games for the season
        ├── teams.parquet   # All teams for the season
        └── game_details.parquet  # Detailed statistics for games
```

### Games DataFrame
Contains basic game information:
- `id`: ESPN game ID
- `date`: Game date and time (ISO format)
- `name`: Game name/description
- `home_team_id`: ESPN ID of home team
- `home_team_name`: Name of home team
- `away_team_id`: ESPN ID of away team
- `away_team_name`: Name of away team
- `home_score`: Final score of home team
- `away_score`: Final score of away team
- `status`: Game status (e.g., "STATUS_FINAL")
- `collection_timestamp`: Time when data was collected

### Teams DataFrame
Contains team information:
- `id`: ESPN team ID
- `name`: Full team name
- `first_seen`: First date the team was observed in data
- `collection_timestamp`: Time when data was collected

### Game Details DataFrame
Contains detailed game statistics and venue information:
- `id`: ESPN game ID
- `venue_id`: ESPN venue ID
- `venue_name`: Name of the venue
- `attendance`: Game attendance
- `home_team_id`: ESPN ID of home team
- `away_team_id`: ESPN ID of away team
- Various team statistics with prefixes `home_` and `away_` (examples):
  - `home_field_goals_made`: Field goals made by home team
  - `home_field_goals_attempted`: Field goals attempted by home team
  - `home_field_goal_pct`: Field goal percentage for home team
  - `home_three_point_field_goals`: Three-pointers made by home team
  - `home_rebounds`: Rebounds by home team
  - `home_assists`: Assists by home team
  - `away_field_goals_made`: Field goals made by away team
  - `away_field_goals_attempted`: Field goals attempted by away team
  - `away_field_goal_pct`: Field goal percentage for away team
- `collection_timestamp`: Time when data was collected

## Debug Mode
The debug mode saves raw API responses to a temporary directory for troubleshooting:

```
/tmp/debug_data/
└── {year}/               # Year portion of the date
    └── response_{date}.json  # Raw API response for that date
```

To access debug data:
```python
import tempfile
from pathlib import Path

# Get the temp directory path
temp_dir = tempfile.gettempdir()

# Construct path to debug files
debug_dir = Path(temp_dir) / "debug_data" / "2023"

# List all debug files
debug_files = list(debug_dir.glob("response_*.json"))
```

## Incremental Updates
The collection pipeline supports incremental updates which:
1. Reads existing Parquet files for the season
2. Only processes new games or games that have changed
3. Efficiently merges new data with existing data
4. Updates game information for changed games

This approach minimizes processing time and API requests for regular updates.

## Command Line Arguments
The collection script supports the following command line arguments:

- `--start-year`: Start year for data collection (default: 2023)
- `--end-year`: End year for data collection (default: 2023)
- `--debug`: Save raw API responses to tmp directory for debugging (default: False)
- `--rate-limit`: Rate limit in seconds between API calls (default: 1.0)
- `--max-retries`: Maximum number of retries for API calls (default: 3)
- `--incremental`: Use incremental update mode (default: False)

## Validation
The collection pipeline includes validation features to ensure data quality:

```bash
# Validate collected data for a specific season
python -m src.data.validate_ncaa_data --season=2023

# Generate validation report for all seasons
python -m src.data.validate_ncaa_data --output
```
