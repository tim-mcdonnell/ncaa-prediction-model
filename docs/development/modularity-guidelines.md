# Modularity Guidelines

This document outlines the principles and practices for maintaining a modular codebase, with a focus on progressive abstraction and practical modularity.

## Core Principles

### 1. Single Responsibility

Each module, class, and function should have a single, well-defined responsibility:

- **Modules** should encapsulate a specific domain concept
- **Classes** should represent a single entity or service
- **Functions** should perform a single, cohesive operation

### 2. Progressive Abstraction

Rather than implementing complex abstractions upfront, use a progressive approach:

- Start with concrete, specific implementations
- Abstract common patterns only when multiple implementations emerge
- Extract interfaces from working implementations, not theoretical needs

### 3. Explicit Data Flow

Make data flow between components explicit and easy to follow:

- Use pipeline modules to orchestrate complex workflows
- Make dependencies between components clear
- Prefer functional transformation pipelines where possible

### 4. Functional Core

Prefer functional patterns for data transformations:

- Use pure functions for data processing
- Build pipelines through function composition
- Separate data transformation from I/O operations

## Directory Structure Guidelines

### Package Organization

- Group related functionality in packages
- Use clear, descriptive package names
- Keep package hierarchy as flat as practical
- Place implementations in appropriately named modules

### Example: Simplified Data Collection Module

```
src/data/collection/
├── __init__.py
├── espn/                # ESPN-specific implementation
│   ├── __init__.py
│   ├── client.py        # HTTP client for ESPN APIs
│   ├── parsers.py       # Parse ESPN responses
│   └── models.py        # Data models for ESPN data
├── connectors/          # HTTP connection management
│   ├── __init__.py
│   ├── http.py          # Basic HTTP connector
│   └── rate_limited.py  # Rate-limited connector
└── extractors/          # Data extraction
    ├── __init__.py
    ├── json.py          # JSON data extractor
    └── html.py          # HTML data extractor
```

## Implementation Patterns

### Start Simple, Refactor Later

Begin with direct implementations and refactor toward abstractions as the need becomes clear:

```python
# Initial implementation - direct and straightforward
class ESPNClient:
    def __init__(self, base_url="https://site.api.espn.com/apis/site/v2/"):
        self.base_url = base_url
        self.http_client = httpx.AsyncClient()
    
    async def fetch_game(self, game_id):
        url = f"{self.base_url}sports/basketball/mens-college-basketball/summary"
        response = await self.http_client.get(url, params={"event": game_id})
        response.raise_for_status()
        return response.json()

# Later, when needed, extract common patterns into abstractions
class DataClient(ABC):
    @abstractmethod
    async def fetch_resource(self, resource_id, resource_type):
        pass

class ESPNClient(DataClient):
    # Implementation using the abstract interface
    pass
```

### Functional Transformations

Use functional patterns for data transformations:

```python
def clean_game_data(game_data: dict) -> dict:
    """Clean raw game data from ESPN API."""
    return {
        "game_id": game_data["id"],
        "date": game_data["date"],
        "home_team_id": game_data["competitions"][0]["competitors"][0]["id"],
        "away_team_id": game_data["competitions"][0]["competitors"][1]["id"],
        "home_score": int(game_data["competitions"][0]["competitors"][0]["score"]),
        "away_score": int(game_data["competitions"][0]["competitors"][1]["score"]),
        "neutral_site": game_data["competitions"][0]["neutralSite"],
    }

def calculate_point_differential(games_df: pl.DataFrame) -> pl.DataFrame:
    """Calculate point differential from game data."""
    return (games_df
        .with_columns([
            (pl.col("home_score") - pl.col("away_score")).alias("point_differential")
        ]))
```

### Pipeline Orchestration

Use pipeline modules to orchestrate complex workflows:

```python
# src/pipelines/collection_pipeline.py
async def collect_season_games(season: int, save: bool = True) -> List[Dict]:
    """Collect all games for a given season."""
    # Initialize ESPN client
    client = ESPNClient()
    
    # Fetch schedule for season
    schedule = await client.fetch_season_schedule(season)
    
    # Extract game IDs
    game_ids = [game["id"] for game in schedule["events"]]
    
    # Fetch individual games
    games = []
    for game_id in game_ids:
        try:
            game_data = await client.fetch_game(game_id)
            clean_data = clean_game_data(game_data)
            games.append(clean_data)
        except Exception as e:
            logger.error(f"Error fetching game {game_id}: {e}")
    
    # Save to Parquet if requested
    if save:
        games_df = pl.DataFrame(games)
        save_path = save_parquet(
            games_df, 
            data_category="raw", 
            filename=f"games/{season}/games"
        )
        logger.info(f"Saved {len(games)} games to {save_path}")
    
    return games
```

### Configuration Management

Use typed configuration with validation:

```python
from pydantic import BaseModel, Field

class ESPNClientConfig(BaseModel):
    """Configuration for ESPN API client."""
    base_url: str = "https://site.api.espn.com/apis/site/v2/"
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_retries: int = Field(default=3, ge=0, le=10)
    rate_limit_per_second: float = Field(default=5.0, gt=0)

def create_espn_client(config: ESPNClientConfig = None) -> ESPNClient:
    """Create an ESPN client with the given configuration."""
    if config is None:
        config = ESPNClientConfig()
    return ESPNClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
        rate_limit=config.rate_limit_per_second
    )
```

## Best Practices for Modularity

1. **Keep modules loosely coupled** - Minimize dependencies between modules
2. **High cohesion within modules** - Related functionality should be grouped together
3. **Explicit dependencies** - Make dependencies explicit, ideally through function parameters
4. **Use pure functions** - Prefer pure functions for data transformations
5. **Follow the Law of Demeter** - Only talk to your immediate friends
6. **Progressive abstraction** - Start simple, abstract later as patterns emerge
7. **Document interfaces** - Clearly document expected behavior and constraints

## Testing Modular Code

1. **Feature-based testing** - Test features/capabilities, not implementation details
2. **Component isolation** - Test components in isolation from their dependencies
3. **Mock dependencies** - Use mocks to isolate the unit under test
4. **Integration testing** - Test how components work together 