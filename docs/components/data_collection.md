# Data Collection

## Overview
The data collection component retrieves NCAA basketball data from ESPN APIs
and stores it in Parquet format for further processing. It supports both full season
collection and incremental updates, with configurable rate limiting to respect ESPN's API constraints.

## Responsibilities
- Fetch game data, team information, and game details from ESPN endpoints
- Handle rate limiting and retries for API requests
- Process and transform API responses to standardized DataFrame format
- Store organized data in Parquet files with a consistent directory structure
- Support incremental updates to efficiently collect only new or changed data
- Provide comprehensive error handling and logging

## Key Classes
- `ESPNClient`: Handles API communication with ESPN, including endpoints for scoreboard, team, and game summary data
- `CollectionPipeline`: Orchestrates the entire data collection process, including game, team, and detailed statistics collection
- `PipelineContext`: Provides execution context with parameters for the pipeline
- `PipelineResult`: Contains results and metadata from pipeline execution

## Usage Examples

```python
# Collect all games for a specific season (full mode)
from src.pipelines.collection_pipeline import CollectionPipeline

# Initialize the pipeline with default settings
pipeline = CollectionPipeline(data_dir="data")

# Collect a complete season
result = await pipeline.collect_season_games(season=2023, mode="full")

# Check if collection was successful
if result.status == PipelineStatus.SUCCESS:
    print(f"Collected {result.metadata['games_count']} games")
else:
    print(f"Collection failed: {result.error}")

# Perform an incremental update for the current season
result = await pipeline.collect_season_games(season=2023, mode="incremental")

# Collect multiple seasons at once
results = await pipeline.collect_all_seasons(start_year=2020, end_year=2023)
```

## Data Flow
1. `CollectionPipeline` initializes and validates parameters
2. Pipeline creates the appropriate directory structure for storing data
3. `ESPNClient` fetches scoreboard data for each date in the season range
4. For each game, metadata is collected and transformed
5. Team information is collected for all teams in the season
6. Game details are collected for each game, extracting statistics from the boxscore
7. All collected data is stored in Parquet files in the season directory:
   - `seasons/{season}/games.parquet`: Basic game information
   - `seasons/{season}/teams.parquet`: Team information
   - `seasons/{season}/game_details.parquet`: Detailed game statistics

## Data Structure
The pipeline organizes data in the following structure:

### Games DataFrame
Contains basic game information:
- `id`: ESPN game ID
- `date`: Game date and time (ISO format)
- `home_team_id`: ESPN ID of home team
- `away_team_id`: ESPN ID of away team
- `home_score`: Final score of home team
- `away_score`: Final score of away team
- `status`: Game status (e.g., "final", "scheduled")
- `collection_timestamp`: Time when data was collected

### Teams DataFrame
Contains team information:
- `id`: ESPN team ID
- `name`: Full team name
- `abbreviation`: Team abbreviation
- `conference_id`: ESPN conference ID
- `conference_name`: Conference name

### Game Details DataFrame
Contains detailed game statistics:
- `id`: ESPN game ID
- Various statistics for home and away teams (e.g., `home_fieldgoalsmade`, `away_threepointers`)
- `venue_id`: ESPN venue ID
- `venue_name`: Venue name
- `attendance`: Game attendance
- `collection_timestamp`: Time when data was collected

## Configuration
The CollectionPipeline can be configured with the following parameters:

```python
CollectionPipeline(
    data_dir="data",          # Base directory for storing data
    rate_limit=5.0,           # Max requests per second
    burst_limit=10            # Max burst of requests allowed
)
```

## Incremental Updates
The pipeline supports an incremental update mode which:
1. Reads existing Parquet files for the season
2. Only collects data for new games or games that have changed
3. Efficiently merges new data with existing data
4. Only updates game details for games that are not yet final

This approach minimizes API requests and processing time for regular updates.

## Error Handling
The pipeline includes robust error handling:
- Individual game or team failures don't cause the entire pipeline to fail
- Failed requests are logged with detailed error information
- The pipeline produces a comprehensive result with success/failure status

## Dependencies
- `aiohttp` or `httpx`: For asynchronous HTTP requests
- `polars`: For DataFrame manipulation and Parquet I/O
- `pydantic`: For data validation and modeling of API responses
