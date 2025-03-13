---
title: ESPN API Integration
description: Documentation for ESPN API endpoints used for NCAA men's basketball data collection
---

# ESPN API Integration Documentation

## Endpoints Overview

| Endpoint | Purpose | Parameters | Notes |
|----------|---------|------------|-------|
| `/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` | Get game data, scores and schedules | dates=YYYYMMDD | Historical data from 2003 |
| `/apis/site/v2/sports/basketball/mens-college-basketball/teams` | Get all teams information | page=n | Pagination available |
| `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}` | Get specific team information | team=team_id or abbreviation | - |
| `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster` | Get detailed team roster information | team=team_id or abbreviation | Includes player details, positions, etc. |
| `/apis/site/v2/sports/basketball/mens-college-basketball/summary` | Get detailed game information | event=game_id | - |
| `/apis/site/v2/sports/basketball/mens-college-basketball/news` | Get latest news | - | - |
| `/apis/site/v2/sports/basketball/mens-college-basketball/rankings` | Get team rankings | - | - |
| `/apis/site/v2/sports/basketball/mens-college-basketball/groups` | Get conference information and teams | - | Alternative to a dedicated conferences endpoint |
| `/apis/v2/sports/basketball/mens-college-basketball/standings` | Get conference standings | - | - |
| `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/schedule` | Get team schedule | season=YYYY, seasontype=n | seasontype: 2=regular, 3=postseason |
| `/v3/sports/basketball/mens-college-basketball/athletes` | Get all current athletes/players | limit=n | Current season only |
| `/v3/sports/basketball/mens-college-basketball/seasons/{year}/athletes` | Get athletes for a specific season | limit=n | - |
| `/v3/sports/basketball/mens-college-basketball/athletes/{playerID}` | Get detailed player information | - | - |
| `/v3/sports/basketball/mens-college-basketball/statistics` | Get team statistics | limit=n | Comprehensive offensive/defensive stats |
| `/v2/sports/basketball/leagues/mens-college-basketball/tournaments/22/seasons/{season}/bracketology` | Get tournament bracket | - | Works for years up to 2021 |

## Base URLs
- Primary base URL: `http://site.api.espn.com`
- Alternative base URLs:
  - `https://sports.core.api.espn.com`
  - `https://data.ncaa.com` (for tournament data)

## Endpoint Details

### Scoreboard Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`
- Parameters:
  - `dates=YYYYMMDD` - Specific date in YYYYMMDD format
  - `limit=n` - Limit number of results
  - `groups=n` - Filter by specific NCAA division (50=Div I)
- Response format: JSON containing game information, scores, team details, and schedule
- Example response:
```json
{
  "events": [
    {
      "id": "401479672",
      "uid": "s:40~l:41~e:401479672",
      "date": "2023-03-01T00:00Z",
      "name": "Wisconsin Badgers at Michigan Wolverines",
      "shortName": "WIS @ MICH",
      "season": {
        "year": 2023,
        "type": 2,
        "slug": "regular-season"
      },
      "competitions": [
        {
          "id": "401479672",
          "uid": "s:40~l:41~e:401479672~c:401479672",
          "date": "2023-03-01T00:00Z",
          "status": {
            "clock": 0,
            "displayClock": "0:00",
            "period": 2,
            "type": {
              "id": "3",
              "name": "STATUS_FINAL",
              "state": "post",
              "completed": true,
              "description": "Final",
              "detail": "Final",
              "shortDetail": "Final"
            }
          },
          "competitors": [
            {
              "id": "130",
              "uid": "s:40~l:41~t:130",
              "type": "team",
              "order": 0,
              "homeAway": "home",
              "team": {
                "id": "130",
                "uid": "s:40~l:41~t:130",
                "location": "Michigan",
                "name": "Wolverines",
                "abbreviation": "MICH",
                "displayName": "Michigan Wolverines",
                "color": "00274C",
                "alternateColor": "ffcb05",
                "logos": [...]
              },
              "score": "87",
              "records": [...]
            },
            {
              "id": "275",
              "uid": "s:40~l:41~t:275",
              "type": "team",
              "order": 1,
              "homeAway": "away",
              "team": {
                "id": "275",
                "uid": "s:40~l:41~t:275",
                "location": "Wisconsin",
                "name": "Badgers",
                "abbreviation": "WIS",
                "displayName": "Wisconsin Badgers",
                "color": "c5050c",
                "alternateColor": "f9f9f9",
                "logos": [...]
              },
              "score": "79",
              "records": [...]
            }
          ],
          "venue": {...}
        }
      ]
    }
  ]
}
```

### Teams Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams`
- Parameters:
  - `page=n` - Get specific page of teams (pagination)
  - `limit=n` - Limit number of results
- Response format: JSON containing team information, logos, colors, and basic data
- Example response:
```json
{
  "sports": [
    {
      "id": "40",
      "uid": "s:40",
      "name": "Basketball",
      "slug": "basketball",
      "leagues": [
        {
          "id": "41",
          "uid": "s:40~l:41",
          "name": "NCAA Men's Basketball",
          "abbreviation": "NCAAM",
          "shortName": "Men's College Basketball",
          "slug": "mens-college-basketball",
          "teams": [
            {
              "id": "52",
              "uid": "s:40~l:41~t:52",
              "slug": "air-force-falcons",
              "location": "Air Force",
              "name": "Falcons",
              "nickname": "Air Force",
              "abbreviation": "AFA",
              "displayName": "Air Force Falcons",
              "shortDisplayName": "Falcons",
              "color": "004a7b",
              "alternateColor": "d9e3ef",
              "isActive": true,
              "isAllStar": false,
              "logos": [...]
            },
            // More teams
          ]
        }
      ]
    }
  ]
}
```

### Team Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}`
- Parameters:
  - `team` - Team ID or abbreviation (e.g., "duke" or "150")
- Response format: JSON containing detailed team information, roster, and schedule
- Example response:
```json
{
  "team": {
    "id": "150",
    "uid": "s:40~l:41~t:150",
    "slug": "duke-blue-devils",
    "location": "Duke",
    "name": "Blue Devils",
    "nickname": "Duke",
    "abbreviation": "DUKE",
    "displayName": "Duke Blue Devils",
    "shortDisplayName": "Blue Devils",
    "color": "001A57",
    "alternateColor": "f1f2f3",
    "isActive": true,
    "isAllStar": false,
    "logos": [...],
    "record": {...},
    "groups": {...},
    "ranks": [...],
    "athletes": [...],
    "coaches": [...],
    "venues": [...]
  }
}
```

### Summary Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary`
- Parameters:
  - `event=game_id` - Game ID (e.g., "401479672")
- Response format: JSON containing detailed game information, play-by-play data, box scores, and team statistics
- Example response:
```json
{
  "boxscore": {
    "teams": [
      {
        "team": {
          "id": "130",
          "uid": "s:40~l:41~t:130",
          "slug": "michigan-wolverines",
          "location": "Michigan",
          "name": "Wolverines",
          "abbreviation": "MICH",
          "displayName": "Michigan Wolverines",
          "shortDisplayName": "Wolverines",
          "color": "00274C",
          "alternateColor": "ffcb05",
          "logo": "..."
        },
        "statistics": [
          {
            "name": "rebounds",
            "displayValue": "34",
            "stat": "rebounds"
          },
          // More statistics
        ]
      },
      // Away team
    ],
    "players": [...]
  },
  "gameInfo": {...},
  "broadcasts": [...],
  "leaders": [...],
  "plays": [...],
  "winprobability": [...]
}
```

### Team Schedule Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/schedule`
- Parameters:
  - `team` - Team ID or abbreviation
  - `season=YYYY` - Season year (e.g., 2024)
  - `seasontype=n` - Season type (2 for regular season, 3 for postseason)
- Response format: JSON containing team's schedule, results, and future games
- Example response:
```json
{
  "count": 31,
  "pageCount": 1,
  "pageIndex": 1,
  "page": 1,
  "items": [
    {
      "id": "401480186",
      "uid": "s:40~l:41~e:401480186",
      "date": "2022-11-07T23:30Z",
      "name": "Jacksonville Dolphins at Duke Blue Devils",
      "shortName": "JAC @ DUKE",
      "season": {
        "year": 2023,
        "type": 2
      },
      "competitions": [
        {
          "id": "401480186",
          "uid": "s:40~l:41~e:401480186~c:401480186",
          "date": "2022-11-07T23:30Z",
          "attendance": 9314,
          "type": {
            "id": "1",
            "shortName": "STD"
          },
          "timeValid": true,
          "neutralSite": false,
          "boxscoreAvailable": true,
          "ticketsAvailable": false,
          "venue": {...},
          "competitors": [...]
        }
      ]
    },
    // More schedule items
  ]
}
```

### Team Roster Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster`
- Parameters:
  - `team` - Team ID or abbreviation (e.g., "duke" or "150")
- Response format: JSON containing detailed team roster information including player details, positions, and more
- Example response:
```json
{
  "timestamp": "2025-03-12T18:19:19Z",
  "status": "success",
  "season": {
    "year": 2025,
    "displayName": "2024-25",
    "type": 2,
    "name": "Regular Season"
  },
  "athletes": [
    {
      "id": "4431890",
      "uid": "s:40~l:41~a:4431890",
      "firstName": "Neal",
      "lastName": "Begovich",
      "fullName": "Neal Begovich",
      "displayName": "Neal Begovich",
      "shortName": "N. Begovich",
      "weight": 230.0,
      "displayWeight": "230 lbs",
      "height": 81.0,
      "displayHeight": "6' 9\"",
      "links": [...],
      "birthPlace": {
        "city": "San Francisco",
        "state": "CA",
        "country": "USA",
        "displayText": "San Francisco, CA"
      },
      "birthCountry": {
        "alternateId": "1",
        "abbreviation": "USA"
      },
      "jersey": "20",
      "position": {
        "id": "2",
        "name": "Forward",
        "displayName": "Forward",
        "abbreviation": "F",
        "leaf": true
      },
      "experience": {
        "years": 4,
        "displayValue": "Senior",
        "abbreviation": "SR"
      },
      "status": {
        "id": "1",
        "name": "Active",
        "type": "active",
        "abbreviation": "Active"
      }
    },
    // More player entries
  ],
  "coach": [
    {
      "id": "31709",
      "firstName": "Jon",
      "lastName": "Scheyer",
      "experience": 0
    }
  ],
  "team": {
    "id": "150",
    "abbreviation": "DUKE",
    "location": "Duke",
    "name": "Blue Devils",
    "displayName": "Duke Blue Devils",
    "clubhouse": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils",
    "color": "013088",
    "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png",
    "recordSummary": "28-3",
    "seasonSummary": "2024-25",
    "standingSummary": "1st in ACC"
  }
}
```

### Groups (Conferences) Endpoint
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/groups`
- Parameters: None required
- Response format: JSON containing conference information and teams within each conference
- Example response includes conference names, abbreviations, and complete team listings in each conference
- Notes: This endpoint serves as the conferences endpoint, providing comprehensive team groupings by conference

### Team Statistics Endpoint (v3 API)
- URL: `https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/statistics`
- Parameters:
  - `limit=n` - Limit number of results (optional)
- Response format: JSON containing comprehensive team statistics
- Example response:
```json
{
  "count": 571,
  "pageIndex": 1,
  "pageSize": 5,
  "pageCount": 115,
  "items": [
    {
      "id": "2",
      "ids": {"team": "2"},
      "type": "team",
      "statistics": {
        "general": {
          "disqualifications": {"value": 5.0},
          "flagrantFouls": {"value": 0.0},
          "fouls": {"value": 577.0},
          "ejections": {"value": 0.0},
          "technicalFouls": {"value": 12.0},
          "rebounds": {"value": 1158.0, "qualified": true},
          "minutes": {"value": 6225.0, "qualified": true},
          "avgMinutes": {"value": 200.80646},
          "avgRebounds": {"value": 37.35484},
          "avgFouls": {"value": 18.612904},
          "assistTurnoverRatio": {"value": 1.8204225, "qualified": true},
          "stealFoulRatio": {"value": 0.3778163},
          // More general stats
        },
        "offensive": {
          "assists": {"value": 517.0, "qualified": true},
          "fieldGoalsAttempted": {"value": 1925.0},
          "fieldGoalsMade": {"value": 934.0},
          "fieldGoalPct": {"value": 0.4851948, "qualified": true},
          "freeThrowPct": {"value": 0.7468944, "qualified": true},
          "points": {"value": 2640.0, "qualified": true},
          "turnovers": {"value": 284.0},
          "threePointFieldGoalPct": {"value": 0.37212276, "qualified": true},
          // More offensive stats
        },
        "defensive": {
          "blocks": {"value": 198.0, "qualified": true},
          "defensiveRebounds": {"value": 792.0},
          "steals": {"value": 218.0, "qualified": true},
          "turnoverPoints": {"value": 488.0},
          "avgDefensiveRebounds": {"value": 25.548388},
          "avgBlocks": {"value": 6.387097},
          "avgSteals": {"value": 7.032258}
        }
      }
    },
    // More team statistics
  ]
}
```
- Notes: Provides extensive statistical categories including general, offensive, and defensive metrics

### Players Endpoint
- URL: `https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/athletes`
- Parameters:
  - `limit=n` - Limit number of results (use large number like 1000000000 to get all)
- Response format: JSON containing player information for the current season
- Example response:
```json
{
  "count": 5782,
  "pageIndex": 1,
  "pageSize": 1000000000,
  "pageCount": 1,
  "items": [
    {
      "id": "5158125",
      "guid": "f75b0cea22c5e38b90efff8f15386271",
      "uid": "s:40~l:41~a:5158125",
      "type": "athlete",
      "alternateIds": {
        "sdr": 5158125
      },
      "firstName": "TJ",
      "lastName": "Power",
      "fullName": "TJ Power",
      "displayName": "TJ Power",
      "shortName": "T. Power",
      "weight": 210,
      "displayWeight": "210 lbs",
      "height": 81,
      "displayHeight": "6' 9\"",
      "age": 19,
      "jersey": "0",
      "position": {
        "id": 5,
        "name": "Forward",
        "displayName": "Forward",
        "abbreviation": "F",
        "leaf": true
      },
      "headshot": {
        "href": "https://a.espncdn.com/i/headshots/mens-college-basketball/players/full/5158125.png",
        "alt": "TJ Power"
      }
    },
    // More players
  ]
}
```

## ESPN API Client Implementation

Our project includes a robust Python client for interacting with ESPN's NCAA basketball APIs, focusing on resilience, error handling, and data parsing.

### Implementation Overview

The ESPN API client is implemented in `src.data.collection.espn.client`, providing a clean, async interface for accessing the most relevant endpoints. Key implementation features include:

- **Asynchronous design:** Utilizes `httpx` for non-blocking HTTP requests
- **Rate limiting:** Implements token bucket algorithm to respect API limits
- **Automatic retries:** Uses exponential backoff with jitter for transient failures
- **Data validation:** Leverages Pydantic models for type-safe API responses
- **Data parsing:** Converts API responses to Polars DataFrames for efficient analysis
- **Comprehensive logging:** Includes detailed logging for debugging and monitoring
- **Error handling:** Robust error handling with clear error messages

### Client Architecture

The client consists of several key components:

1. **ESPNClient:** The main client class that interacts with ESPN endpoints
2. **RateLimiter:** Implements the token bucket algorithm for API rate limiting
3. **Pydantic models:** Type-safe representations of API responses
4. **Data parsers:** Convert API responses into structured DataFrames

### API Methods

#### `get_scoreboard(date_str: str) -> pl.DataFrame`

Retrieves scoreboard data for a specific date.

- **Parameters:**
  - `date_str`: Date in YYYYMMDD format (e.g., "20230301" for March 1, 2023)
- **Returns:** DataFrame containing game data
- **Raises:** ValueError if the date format is invalid
- **Example:**
  ```python
  games_df = await client.get_scoreboard("20230301")
  ```

#### `get_scoreboard_for_date_range(start_date_str: str, end_date_str: str) -> pl.DataFrame`

Retrieves scoreboard data for a range of dates.

- **Parameters:**
  - `start_date_str`: Start date in YYYYMMDD format
  - `end_date_str`: End date in YYYYMMDD format
- **Returns:** DataFrame containing game data for all dates in the range
- **Raises:** 
  - ValueError if either date string is invalid
  - ValueError if end_date is before start_date
- **Example:**
  ```python
  games_df = await client.get_scoreboard_for_date_range("20230301", "20230307")
  ```

#### `get_game_summary(game_id: str) -> GameSummaryResponse`

Retrieves detailed game summary data.

- **Parameters:**
  - `game_id`: ESPN game ID
- **Returns:** Game summary response object
- **Example:**
  ```python
  summary = await client.get_game_summary("401468461")
  ```

#### `get_team(team_id: str) -> TeamResponse`

Retrieves information for a specific team.

- **Parameters:**
  - `team_id`: ESPN team ID
- **Returns:** Team response object
- **Example:**
  ```python
  team = await client.get_team("52")  # Air Force Falcons
  ```

#### `get_teams(page: int = 1) -> TeamsResponse`

Retrieves a list of teams with pagination.

- **Parameters:**
  - `page`: Page number for pagination (default: 1)
- **Returns:** Teams response object
- **Example:**
  ```python
  teams_page1 = await client.get_teams(page=1)
  ```

#### `get_all_teams() -> List[Team]`

Retrieves all teams across all pages, handling pagination automatically.

- **Returns:** List of Team objects
- **Example:**
  ```python
  all_teams = await client.get_all_teams()
  ```

### Client Configuration

The `ESPNClient` constructor accepts the following parameters:

- `rate_limit`: Number of requests allowed per second (default: 5.0)
- `burst_limit`: Maximum number of requests that can be made at once (default: 10)
- `timeout`: Default timeout for HTTP requests in seconds (default: 30.0)

Example with custom configuration:

```python
async with ESPNClient(rate_limit=2.0, burst_limit=5, timeout=60.0) as client:
    # Client will now make at most 2 requests per second
    # with a burst capacity of 5 requests
    # and a 60-second timeout
    ...
```

### Date Validation

The client implements strict date validation:

- Dates must be in YYYYMMDD format (e.g., "20230301" for March 1, 2023)
- Dates are validated to ensure they represent valid calendar dates
- Invalid dates (like February 31st) will raise a ValueError

The client also checks for date mismatches between requested dates and returned event dates, which helps detect when the ESPN API silently "corrects" an invalid date.

### Error Handling

The client provides robust error handling for various scenarios:

- **Network errors:** Automatically retried with exponential backoff
- **API errors:** HTTP status errors are raised with detailed information
- **Invalid inputs:** Clear validation errors for invalid parameters
- **Date validation:** Strict validation for date formats and ranges

### Usage Example

```python
import asyncio
import logging
from src.data.collection.espn.client import ESPNClient

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    # Create a client with default rate limits
    async with ESPNClient() as client:
        # Get games for a specific date
        games_df = await client.get_scoreboard("20230301")
        print(f"Found {len(games_df)} games on March 1, 2023")
        
        # Get games for a date range
        games_range_df = await client.get_scoreboard_for_date_range("20230301", "20230307")
        print(f"Found {len(games_range_df)} games from March 1-7, 2023")
        
        # Get all NCAA basketball teams
        teams = await client.get_all_teams()
        print(f"Found {len(teams)} teams")
        
        # Get detailed game information
        game_summary = await client.get_game_summary("401468461")
        print(f"Game: {game_summary.header.competitions[0].competitors[0].team.name} vs "
              f"{game_summary.header.competitions[0].competitors[1].team.name}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

### Limitations and Known Issues

- The ESPN API may have undocumented rate limits or change without notice
- Some endpoints may return inconsistent data formats
- The API sometimes returns dates in different time zones, which can cause date mismatches
- Empty results may be returned for valid dates with no games
- The API may silently "correct" invalid dates (e.g., February 31st might return data for February 28th)

### Testing

The client includes comprehensive tests covering:

- Date validation
- Rate limiting
- Retry functionality
- Response parsing
- Error handling
- Pagination logic

Run the tests with:

```bash
# Run all tests
python -m pytest tests/data/collection/espn/

# Run specific test
python -m pytest tests/data/collection/espn/test_client.py::TestESPNClient::test_get_scoreboard_for_date_range
```

## Historical Data Availability

Based on research, the ESPN API provides data back to approximately 2003 for NCAA men's basketball. However, there are some considerations:

1. **Data completeness**: More recent seasons (2010 onwards) have more complete data
2. **Play-by-play data**: Available for most games from around 2010 onwards
3. **Older seasons**: May have limited statistics or missing games
4. **Historical player data**: Prior seasons' player data requires querying individual player IDs

## URL Parameters and Filters

The ESPN API supports several common parameters across endpoints:

- `limit`: Maximum number of items to return
- `groups`: Filter by division (e.g., 50 for Division I)
- `page`/`pageIndex`: Page number for paginated results
- `dates`: Filter by specific date(s) in YYYYMMDD format
- `season`: Filter by season year (e.g., 2024)
- `seasontype`: Filter by season type (2=regular season, 3=postseason)
- `lang`: Language for response text (default is "en")

## API Limitations and Inconsistencies

1. **No official documentation**: ESPN does not officially document these APIs, so they may change without notice
2. **Rate limiting**: Excessive requests may lead to temporary blocking
3. **Inconsistent structures**: Response structures can vary across endpoints and seasons
4. **Tournament bracket endpoints**: Historical tournament bracket data may have different endpoints for different years
5. **Player data challenges**: Getting historical player data requires individual player ID lookups
6. **Endpoint naming conventions**: Some resources (like conferences) are available under alternative names (e.g., "groups")
7. **Base URL variations**: Some endpoints use the v2 API path, while others use v3, requiring different base URLs

## Recommended Approach for Data Collection

1. **Incremental collection**: Process one season at a time, with daily increments during active seasons
2. **Paginated requests**: Use pagination where available
3. **Exponential backoff**: Implement retry logic with increasing delays
4. **Respect ESPN resources**: Add reasonable delays between requests (e.g., 1-2 seconds)
5. **Data normalization**: Standardize responses as they might vary across years
6. **Selective storage**: Only store relevant fields to minimize storage requirements
7. **Conference data**: Use the `/groups` endpoint for conference information rather than trying to find a dedicated conferences endpoint
8. **Team details**: Consider combining team information from both the team endpoint and the team roster endpoint
9. **Statistics collection**: Utilize the v3 statistics endpoint for comprehensive team statistics data

## Additional Resources

1. [sportsdataverse/hoopR GitHub repository](https://github.com/sportsdataverse/hoopR)
2. [ESPN hidden API endpoints Gist](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b)
3. [hoopR R package documentation](https://hoopr.sportsdataverse.org/) 

## Error Handling Patterns

The ESPN API can be subject to rate limiting, inconsistent responses, and service outages. Following the project's resilience patterns, here are recommended approaches for robust error handling:

### Retry Pattern with Exponential Backoff

```python
from src.utils.resilience.retry import retry
import httpx
import polars as pl
import asyncio
from typing import Dict, Any

@retry(max_attempts=3, backoff_factor=1.5, exceptions=(httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError))
async def fetch_scoreboard_data(date: str) -> Dict[str, Any]:
    """
    Fetch scoreboard data for a specific date with retry logic.
    
    Args:
        date: Date string in YYYYMMDD format
        
    Returns:
        Dictionary containing the API response data
        
    Raises:
        httpx.HTTPError: If the request fails after all retry attempts
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={date}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Usage example
async def get_games(date: str) -> pl.DataFrame:
    try:
        data = await fetch_scoreboard_data(date)
        # Process data using Polars
        events = data.get("events", [])
        if not events:
            return pl.DataFrame(schema={"game_id": pl.Utf8, "home_team": pl.Utf8, "away_team": pl.Utf8, "date": pl.Utf8})
        
        # Extract game information
        games = []
        for event in events:
            game_id = event.get("id")
            competitions = event.get("competitions", [])
            if not competitions:
                continue
                
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            if len(competitors) != 2:
                continue
                
            home_team = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away_team = next((c for c in competitors if c.get("homeAway") == "away"), {})
            
            games.append({
                "game_id": game_id,
                "home_team": home_team.get("team", {}).get("displayName", "Unknown"),
                "away_team": away_team.get("team", {}).get("displayName", "Unknown"),
                "date": event.get("date")
            })
        
        return pl.DataFrame(games)
    except Exception as e:
        # Log error appropriately
        print(f"Error fetching games for date {date}: {str(e)}")
        # Return empty DataFrame with expected schema
        return pl.DataFrame(schema={"game_id": pl.Utf8, "home_team": pl.Utf8, "away_team": pl.Utf8, "date": pl.Utf8})
```

### Circuit Breaker Pattern

For more advanced error handling, consider implementing a circuit breaker pattern to prevent overwhelming the ESPN API during outages:

```python
from src.utils.resilience.circuit_breaker import circuit_breaker
import httpx
import polars as pl
from typing import Dict, Any

@circuit_breaker(failure_threshold=5, recovery_timeout=60, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def fetch_team_data(team_id: str) -> Dict[str, Any]:
    """
    Fetch team data with circuit breaker pattern.
    
    Args:
        team_id: ESPN team ID
        
    Returns:
        Dictionary containing the API response data
        
    Raises:
        CircuitBreakerOpenError: If circuit breaker is open
        httpx.HTTPError: If the request fails
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Token Bucket Rate Limiting

To respect ESPN's resources and avoid being blocked:

```python
from src.utils.resilience.rate_limiter import RateLimiter
import asyncio
import httpx

# Create a rate limiter allowing 1 request per second
rate_limiter = RateLimiter(tokens=1, refill_rate=1.0)

async def fetch_with_rate_limit(url: str) -> Dict[str, Any]:
    """
    Fetch data with rate limiting.
    
    Args:
        url: API endpoint URL
        
    Returns:
        Dictionary containing the API response data
    """
    # Wait until a token is available
    await rate_limiter.acquire()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Comprehensive Error Handling

Combining multiple resilience patterns for comprehensive error handling:

```python
from src.utils.resilience.retry import retry
from src.utils.resilience.circuit_breaker import circuit_breaker
from src.utils.resilience.rate_limiter import RateLimiter
import httpx
import polars as pl
import asyncio
from typing import Dict, Any, List

# Global rate limiter
rate_limiter = RateLimiter(tokens=1, refill_rate=1.0)

@retry(max_attempts=3, backoff_factor=1.5)
@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def fetch_espn_data(url: str) -> Dict[str, Any]:
    """
    Fetch data from ESPN API with comprehensive error handling.
    
    Args:
        url: API endpoint URL
        
    Returns:
        Dictionary containing the API response data
    """
    # Apply rate limiting
    await rate_limiter.acquire()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

## Testing Approach for ESPN API Integration

Following the project's test-driven development approach, here are examples of tests for the ESPN API integration:

### 1. Unit Tests for API Client

```python
# tests/data/collection/espn/test_client.py
import pytest
import polars as pl
from unittest.mock import patch, MagicMock
from src.data.collection.espn.client import ESPNClient

@pytest.fixture
def mock_scoreboard_response():
    """Return a fixture with sample scoreboard data"""
    return {
        "events": [
            {
                "id": "401479672",
                "date": "2023-03-01T00:00Z",
                "name": "Wisconsin Badgers at Michigan Wolverines",
                "competitions": [
                    {
                        "id": "401479672",
                        "competitors": [
                            {
                                "id": "130",
                                "homeAway": "home",
                                "team": {
                                    "id": "130",
                                    "displayName": "Michigan Wolverines"
                                },
                                "score": "87"
                            },
                            {
                                "id": "275",
                                "homeAway": "away",
                                "team": {
                                    "id": "275",
                                    "displayName": "Wisconsin Badgers"
                                },
                                "score": "79"
                            }
                        ]
                    }
                ]
            }
        ]
    }

class TestESPNClient:
    @patch("src.data.collection.espn.client.httpx.AsyncClient")
    async def test_get_scoreboard(self, mock_client, mock_scoreboard_response):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_scoreboard_response
        mock_response.raise_for_status = MagicMock()
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Initialize client and call method
        client = ESPNClient()
        result = await client.get_scoreboard("20230301")
        
        # Assertions
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert "game_id" in result.columns
        assert "home_team" in result.columns
        assert "away_team" in result.columns
        assert result[0, "home_team"] == "Michigan Wolverines"
        assert result[0, "away_team"] == "Wisconsin Badgers"
        assert result[0, "home_score"] == "87"
        assert result[0, "away_score"] == "79"
        
    @patch("src.data.collection.espn.client.httpx.AsyncClient")
    async def test_get_scoreboard_handles_empty_data(self, mock_client):
        # Setup mock response with empty data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_response.raise_for_status = MagicMock()
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Initialize client and call method
        client = ESPNClient()
        result = await client.get_scoreboard("20230301")
        
        # Assertions
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert "game_id" in result.columns
        assert "home_team" in result.columns
        assert "away_team" in result.columns
```

### 2. Integration Tests with Response Fixtures

```python
# tests/data/collection/espn/test_integration.py
import pytest
import polars as pl
import json
import os
from src.data.collection.espn.client import ESPNClient
from src.data.storage.parquet_io import load_parquet, save_parquet

@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory"""
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "espn")

@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file from the fixtures directory"""
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load

class TestESPNIntegration:
    @pytest.mark.integration
    @pytest.mark.parametrize("fixture_file,expected_count", [
        ("scoreboard_20230301.json", 45),
        ("scoreboard_20230302.json", 32),
    ])
    async def test_scoreboard_to_dataframe(self, load_fixture, fixture_file, expected_count):
        """Test processing scoreboard data from fixtures to DataFrame"""
        # Load fixture data
        data = load_fixture(fixture_file)
        
        # Process with client method directly
        client = ESPNClient()
        result = client._process_scoreboard_data(data)
        
        # Assertions
        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == expected_count
        assert all(col in result.columns for col in ["game_id", "home_team", "away_team", "date"])
        
    @pytest.mark.integration
    async def test_save_scoreboard_data(self, load_fixture, tmp_path):
        """Test saving scoreboard data to Parquet"""
        # Load fixture data
        data = load_fixture("scoreboard_20230301.json")
        
        # Process with client
        client = ESPNClient()
        result = client._process_scoreboard_data(data)
        
        # Save to temporary path
        date_str = "20230301"
        filename = f"games/{date_str[:4]}/games_{date_str}"
        save_path = os.path.join(tmp_path, "raw", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save data
        result.write_parquet(save_path + ".parquet")
        
        # Read it back and verify
        loaded_df = pl.read_parquet(save_path + ".parquet")
        assert loaded_df.shape == result.shape
        assert loaded_df.columns == result.columns
```

### 3. Mock Tests for Error Handling

```python
# tests/data/collection/espn/test_error_handling.py
import pytest
import polars as pl
from unittest.mock import patch, MagicMock
import httpx
from src.data.collection.espn.client import ESPNClient

class TestESPNErrorHandling:
    @patch("src.data.collection.espn.client.httpx.AsyncClient")
    async def test_retry_on_timeout(self, mock_client):
        """Test that retry logic works on timeout errors"""
        # Setup mock to raise timeout error once, then succeed
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"events": []}
        mock_response_success.raise_for_status = MagicMock()
        
        mock_client_instance = MagicMock()
        # First call raises timeout, second succeeds
        mock_client_instance.__aenter__.return_value.get.side_effect = [
            httpx.TimeoutException("Connection timeout"),
            mock_response_success
        ]
        mock_client.return_value = mock_client_instance
        
        # Initialize client and call method
        client = ESPNClient()
        result = await client.get_scoreboard("20230301")
        
        # Verify retry worked and we got a result
        assert isinstance(result, pl.DataFrame)
        assert mock_client_instance.__aenter__.return_value.get.call_count == 2
        
    @patch("src.data.collection.espn.client.httpx.AsyncClient")
    async def test_circuit_breaker_opens(self, mock_client):
        """Test that circuit breaker opens after multiple failures"""
        # Setup mock to always raise errors
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.get.side_effect = httpx.HTTPError("Server error")
        mock_client.return_value = mock_client_instance
        
        # Initialize client
        client = ESPNClient()
        
        # Make multiple calls to trigger circuit breaker
        with pytest.raises(Exception) as excinfo:
            for _ in range(6):  # Assuming threshold is 5
                await client.get_scoreboard("20230301")
                
        # Verify circuit breaker error
        assert "circuit" in str(excinfo.value).lower()
```

### 4. Test for Data Storage Integration

```python
# tests/data/collection/espn/test_storage.py
import pytest
import polars as pl
import os
from src.data.collection.espn.client import ESPNClient
from src.data.storage.parquet_io import save_parquet, load_parquet

class TestESPNStorage:
    @pytest.mark.parametrize("date_str", ["20230301", "20230302"])
    async def test_end_to_end_collection_and_storage(self, date_str, tmp_path, monkeypatch):
        """Test end-to-end collection and storage process"""
        # Setup mock environment
        monkeypatch.setenv("DATA_ROOT", str(tmp_path))
        
        # Initialize client with mocked API calls (implementation depends on your setup)
        client = ESPNClient()
        
        # Mock the actual API call (implementation will vary based on your setup)
        # ...
        
        # Test the collection and storage
        await client.collect_and_store_games(date_str)
        
        # Verify data was saved properly
        expected_path = os.path.join(tmp_path, "raw", "games", date_str[:4], f"games_{date_str}.parquet")
        assert os.path.exists(expected_path)
        
        # Load and verify data structure
        df = load_parquet("raw", f"games/{date_str[:4]}/games_{date_str}")
        assert isinstance(df, pl.DataFrame)
        assert "game_id" in df.columns
        assert "home_team" in df.columns
        assert "away_team" in df.columns
```

These testing examples demonstrate the project's recommended test-driven development approach, covering:

1. Unit tests for the API client functionality
2. Integration tests using fixture data
3. Tests for error handling and resilience patterns
4. End-to-end tests for data collection and storage

Each test focuses on a specific aspect of the API integration, ensuring that all components work correctly in isolation and together. Following this pattern will help maintain a robust and reliable data collection system for the NCAA Basketball Prediction Model. 