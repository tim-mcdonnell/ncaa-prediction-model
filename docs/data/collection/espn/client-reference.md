---
title: ESPN Client Technical Reference
description: Technical reference for the ESPNClient class including all methods, parameters, and error handling
---

# ESPN Client Technical Reference

This document provides a complete technical reference for the `ESPNClient` class, detailing all public methods, their parameters, return types, and error handling behaviors.

## Class Overview

The `ESPNClient` class is an asynchronous HTTP client for interacting with ESPN's NCAA basketball APIs. It follows the project's resilience patterns with built-in rate limiting and retry logic.

```python
class ESPNClient:
    """Client for interacting with ESPN's NCAA basketball APIs."""
    
    def __init__(
        self,
        rate_limit: float = 5.0,  # requests per second
        burst_limit: int = 10,
        timeout: float = 30.0,
    ):
        """
        Initialize ESPN client.
        
        Args:
            rate_limit: Number of requests allowed per second
            burst_limit: Maximum number of requests that can be made at once
            timeout: Default timeout for HTTP requests in seconds
        """
```

## Context Manager Protocol

The client implements the asynchronous context manager protocol for automatic resource management:

```python
async def __aenter__(self) -> 'ESPNClient':
    """Async context manager entry."""
    
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Async context manager exit."""
```

## Method Reference

### Game Information

#### `get_scoreboard`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_scoreboard(self, date_str: str) -> pl.DataFrame:
    """
    Get scoreboard data for a specific date.
    
    Args:
        date_str: Date in YYYYMMDD format
        
    Returns:
        DataFrame containing game data
        
    Raises:
        ValueError: If the date_str is not a valid date
    """
```

#### `get_scoreboard_for_date_range`

```python
async def get_scoreboard_for_date_range(
    self, start_date: str, end_date: str
) -> pl.DataFrame:
    """
    Get scoreboard data for a range of dates.
    
    Args:
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        
    Returns:
        DataFrame containing game data for the date range
        
    Raises:
        ValueError: If either date is invalid or if end_date is before start_date
    """
```

#### `get_game_summary`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_game_summary(self, game_id: str) -> pl.DataFrame:
    """
    Get detailed information for a specific game.
    
    Args:
        game_id: ESPN game ID
        
    Returns:
        DataFrame containing detailed game information
        
    Raises:
        ValueError: If game_id is empty
    """
```

### Team Information

#### `get_teams`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_teams(self, page: int = 1) -> pl.DataFrame:
    """
    Get all teams (paginated).
    
    Args:
        page: Page number (1-indexed)
        
    Returns:
        DataFrame containing team information
        
    Raises:
        ValueError: If page is less than 1
    """
```

#### `get_team`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_team(self, team_id: str) -> pl.DataFrame:
    """
    Get information for a specific team.
    
    Args:
        team_id: ESPN team ID or abbreviation
        
    Returns:
        DataFrame containing team information
        
    Raises:
        ValueError: If team_id is empty
    """
```

#### `get_team_roster`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_team_roster(self, team_id: str) -> pl.DataFrame:
    """
    Get detailed roster information for a team.
    
    Args:
        team_id: ESPN team ID or abbreviation
        
    Returns:
        DataFrame containing roster information
        
    Raises:
        ValueError: If team_id is empty
    """
```

#### `get_team_schedule`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_team_schedule(
    self, team_id: str, season: Optional[str] = None, season_type: int = 2
) -> pl.DataFrame:
    """
    Get schedule for a specific team.
    
    Args:
        team_id: ESPN team ID or abbreviation
        season: Season year (e.g., "2023")
        season_type: Season type (2=regular season, 3=postseason)
        
    Returns:
        DataFrame containing schedule information
        
    Raises:
        ValueError: If team_id is empty
    """
```

### Conferences and Standings

#### `get_groups`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_groups(self) -> pl.DataFrame:
    """
    Get conference (group) information.
    
    Returns:
        DataFrame containing conference information
    """
```

#### `get_standings`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_standings(self) -> pl.DataFrame:
    """
    Get current conference standings.
    
    Returns:
        DataFrame containing standings information
    """
```

### Rankings

#### `get_rankings`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_rankings(self) -> pl.DataFrame:
    """
    Get current team rankings.
    
    Returns:
        DataFrame containing ranking information
    """
```

### Athletes/Players

#### `get_athletes`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_athletes(self, limit: int = 50) -> pl.DataFrame:
    """
    Get current athletes/players.
    
    Args:
        limit: Maximum number of athletes to return
        
    Returns:
        DataFrame containing athlete information
        
    Raises:
        ValueError: If limit is less than 1
    """
```

#### `get_athletes_by_season`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_athletes_by_season(
    self, season: str, limit: int = 50
) -> pl.DataFrame:
    """
    Get athletes for a specific season.
    
    Args:
        season: Season year (e.g., "2023")
        limit: Maximum number of athletes to return
        
    Returns:
        DataFrame containing athlete information
        
    Raises:
        ValueError: If season is empty or limit is less than 1
    """
```

#### `get_athlete`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_athlete(self, athlete_id: str) -> pl.DataFrame:
    """
    Get detailed information for a specific athlete.
    
    Args:
        athlete_id: ESPN athlete ID
        
    Returns:
        DataFrame containing detailed athlete information
        
    Raises:
        ValueError: If athlete_id is empty
    """
```

### Team Statistics

#### `get_team_statistics`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_team_statistics(self, limit: int = 50) -> pl.DataFrame:
    """
    Get comprehensive team statistics.
    
    Args:
        limit: Maximum number of teams to return
        
    Returns:
        DataFrame containing team statistics
        
    Raises:
        ValueError: If limit is less than 1
    """
```

### Tournament Information

#### `get_tournament_bracket`

```python
@retry(max_attempts=3, backoff_factor=2.0)
async def get_tournament_bracket(self, season: str) -> pl.DataFrame:
    """
    Get tournament bracket for a specific season.
    
    Args:
        season: Season year (e.g., "2023")
        
    Returns:
        DataFrame containing bracket information
        
    Raises:
        ValueError: If season is empty
    """
```

## Error Handling

All public methods in the `ESPNClient` implement error handling following the project's resilience patterns:

1. **HTTP Errors**: Automatically retried with exponential backoff using the `@retry` decorator
2. **Input Validation**: Parameters are validated before making API calls
3. **Response Validation**: API responses are validated using Pydantic models

### Common Exception Types

| Exception Type | Meaning | Handling Strategy |
|----------------|---------|-------------------|
| `ValueError` | Invalid input parameters | Fix the input parameters |
| `httpx.HTTPError` | HTTP-related errors | Automatically retried, then bubbled up |
| `httpx.TimeoutException` | Request timeout | Automatically retried, then bubbled up |
| `httpx.ConnectError` | Connection error | Automatically retried, then bubbled up |
| `ValidationError` | Invalid API response | Logged as an error, then bubbled up |

## Resource Management

The `ESPNClient` manages resources through the asynchronous context manager protocol:

```python
async with ESPNClient() as client:
    # Client is initialized here
    # HTTP client is created
    
# When exiting the context:
# - HTTP connections are properly closed
# - Resources are released
```

## Rate Limiting

The client uses a token bucket algorithm for rate limiting:

```python
# Default: 5 requests per second with burst of 10
client = ESPNClient(rate_limit=5.0, burst_limit=10)
```

The rate limiter ensures:
- Requests are evenly distributed over time
- Burst capacity for sudden spikes in requests
- Automatic waiting when rate limit is reached

## Performance Considerations

For optimal performance with the `ESPNClient`:

1. **Reuse the client**: Create a single client instance and reuse it
2. **Adjust rate limits**: For faster processing, increase rate limits if the API allows
3. **Use batch methods**: For retrieving multiple items, use methods that support batching
4. **Process incrementally**: For large datasets, process data as it arrives

## Implementation Notes

- All public methods return `pl.DataFrame` for consistency with the project's data processing pipeline
- Date parameters use the format `YYYYMMDD` (e.g., "20231125" for November 25, 2023)
- IDs are always passed as strings, even when they consist of numeric characters
- Logging is extensive and follows the project's logging conventions 