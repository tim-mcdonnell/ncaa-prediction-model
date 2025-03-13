---
title: ESPN Client Usage Guide
description: Comprehensive guide for using the ESPNClient with examples of all endpoints and common interaction patterns
---

# ESPN Client Usage Guide

This guide provides detailed examples for using the `ESPNClient` to interact with ESPN's NCAA basketball APIs. The client is designed to follow the project's resilience patterns, with built-in rate limiting and retry logic.

## Basic Usage

The `ESPNClient` is designed to be used as an asynchronous context manager to ensure proper resource cleanup:

```python
import asyncio
from src.data.collection.espn.client import ESPNClient

async def main():
    # Create a client with default rate limits (5 requests/second, burst of 10)
    async with ESPNClient() as client:
        # Use the client to fetch data
        games_df = await client.get_scoreboard("20230301")
        
        # Process the data (returns Polars DataFrame)
        print(f"Found {len(games_df)} games")

# Run the async function
asyncio.run(main())
```

## Configuring Rate Limits

You can configure the rate limiter when creating the client:

```python
# Create a more conservative client (2 requests/second, burst of 5)
async with ESPNClient(rate_limit=2.0, burst_limit=5) as client:
    # Use client methods
```

## Common Interaction Patterns

### Fetching Game Data

#### Single Day

```python
# Get games for a specific date
games_df = await client.get_scoreboard("20230301")  # March 1, 2023
```

#### Date Range

```python
# Get games for a date range
games_range_df = await client.get_scoreboard_for_date_range(
    start_date="20230301",  # March 1, 2023
    end_date="20230307"     # March 7, 2023
)
```

#### Game Details

```python
# Get detailed information for a specific game
game_details_df = await client.get_game_summary("401524691")  # Game ID
```

### Team Information

#### All Teams

```python
# Get all teams (paginated)
teams_df = await client.get_teams()

# Get specific page of teams
teams_page2_df = await client.get_teams(page=2)
```

#### Specific Team

```python
# Get information for a specific team by ID
team_df = await client.get_team("52")  # Air Force

# Get information for a specific team by abbreviation
duke_df = await client.get_team("DUKE")
```

#### Team Roster

```python
# Get detailed roster information for a team
roster_df = await client.get_team_roster("52")  # Air Force
```

#### Team Schedule

```python
# Get team schedule for current season
schedule_df = await client.get_team_schedule("52")  # Air Force

# Get team schedule for a specific season
schedule_2022_df = await client.get_team_schedule("52", season="2022")
```

### Conference and Standings

#### Conferences

```python
# Get all conferences (groups)
conferences_df = await client.get_groups()
```

#### Conference Standings

```python
# Get current standings
standings_df = await client.get_standings()
```

### Rankings

```python
# Get current team rankings
rankings_df = await client.get_rankings()
```

### Players/Athletes

```python
# Get current athletes (paginated)
athletes_df = await client.get_athletes(limit=100)

# Get athletes for a specific season
athletes_2022_df = await client.get_athletes_by_season("2022", limit=100)

# Get detailed information for a specific athlete
player_df = await client.get_athlete("4433137")  # Player ID
```

### Team Statistics

```python
# Get comprehensive team statistics
stats_df = await client.get_team_statistics(limit=50)
```

### Tournament Bracket

```python
# Get tournament bracket for a specific season
bracket_df = await client.get_tournament_bracket("2023")
```

## Handling Errors

The client includes automatic retry logic for transient failures. However, you may want to implement additional error handling:

```python
try:
    games_df = await client.get_scoreboard("20230301")
except ValueError as e:
    # Handle validation errors (e.g., invalid date format)
    print(f"Validation error: {str(e)}")
except httpx.HTTPError as e:
    # Handle HTTP errors that weren't resolved by retry logic
    print(f"HTTP error: {str(e)}")
```

## Logging

The client includes comprehensive logging. To configure logging:

```python
import logging

# Configure logging to see client operations
logging.basicConfig(level=logging.INFO)

# For more detailed logging (including HTTP requests)
logging.getLogger("src.data.collection.espn.client").setLevel(logging.DEBUG)
```

## Batch Processing

For processing large amounts of data, consider using semaphores to limit concurrency:

```python
import asyncio
from src.data.collection.espn.client import ESPNClient

async def fetch_season_data(year):
    # Create date range for a season
    start_date = f"{year}1101"  # November 1st
    end_date = f"{year+1}0401"  # April 1st next year
    
    async with ESPNClient() as client:
        # Limit concurrency to avoid overwhelming the API
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def fetch_with_limit(date_str):
            async with semaphore:
                return await client.get_scoreboard(date_str)
        
        # Generate all dates in the range
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        dates = [(start + timedelta(days=i)).strftime("%Y%m%d") 
                for i in range((end - start).days + 1)]
        
        # Create tasks for all dates
        tasks = [fetch_with_limit(date) for date in dates]
        
        # Run all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_dfs = [df for df in results if not isinstance(df, Exception)]
        if valid_dfs:
            return pl.concat(valid_dfs)
        return pl.DataFrame()

# Run the async function
season_data = asyncio.run(fetch_season_data(2023))
```

## Performance Considerations

1. **Connection Pooling**: The client manages HTTP connections efficiently, but for long-running tasks, consider creating a new client periodically.

2. **Memory Usage**: When fetching large datasets, process data incrementally rather than keeping everything in memory.

3. **Rate Limiting**: The default rate limits are conservative. For time-sensitive tasks, you can increase them but be mindful of API restrictions.

## Integration with Collection Pipeline

The `ESPNClient` is designed to be used within the Collection Pipeline:

```python
from src.data.collection.espn.client import ESPNClient
from src.pipelines.collection_pipeline import CollectionPipeline

class ESPNCollector:
    async def collect_games(self, start_date, end_date):
        async with ESPNClient() as client:
            return await client.get_scoreboard_for_date_range(start_date, end_date)
    
    # Other collection methods...

# Usage in pipeline
collector = ESPNCollector()
pipeline = CollectionPipeline(collectors=[collector])
pipeline.run()
``` 