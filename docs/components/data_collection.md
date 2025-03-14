# Data Collection

## Overview
The data collection component retrieves NCAA basketball data from ESPN APIs
and stores it in Parquet format for further processing.

## Responsibilities
- Fetch game data from ESPN endpoints
- Handle rate limiting and retries
- Convert API responses to standardized DataFrame format
- Store raw data in Parquet files
- Support incremental updates for new/changed games

## Key Classes
- `ESPNClient`: Handles API communication with ESPN
- `CollectionPipeline`: Orchestrates the data collection process
- `ParquetIO`: Manages reading/writing Parquet files

## Usage Examples

```python
# Collect all games for the current season
from src.pipelines import CollectionPipeline

pipeline = CollectionPipeline()
pipeline.run(season=2023)

# Collect specific games
pipeline.run(season=2023, game_ids=["401468511", "401468512"])
```

## Data Flow
1. `ESPNClient` fetches data from ESPN endpoints
2. Data is converted to standardized DataFrame format
3. `ParquetIO` writes data to Parquet files in `data/raw/{season}/`
4. Metadata is updated to track collected games

## Configuration
Collection behavior can be configured in `configs/collection.toml`:

```toml
[espn]
base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
rate_limit = 100  # requests per minute

[storage]
data_dir = "data/"
``` 