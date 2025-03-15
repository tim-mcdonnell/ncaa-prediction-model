# Historical Data Collection

## Overview
The historical data collection script is responsible for gathering, validating, and storing NCAA basketball data from 2000 to 2025 using the collection pipeline and data cleaning infrastructure. It represents the initial data collection effort that builds the foundation for the prediction model.

## Responsibilities
- Collect complete NCAA basketball data for specified seasons (default 2000-2025)
- Validate all collected data for quality and completeness
- Store data efficiently in Parquet format
- Generate comprehensive data quality reports
- Document any gaps or issues in historical data
- Create data collection progress reports
- Handle API rate limits and failures gracefully

## Key Classes
- `HistoricalDataCollector`: Orchestrates the collection and processing of historical data
- `CollectionPipeline`: Handles the communication with ESPN API
- `DataCleaner`: Validates and cleans the collected data

## Usage Examples

### Basic Usage
```bash
# Run with default settings (2000-2025)
python -m src.scripts.historical_data_collection

# Run for specific years
python -m src.scripts.historical_data_collection --start-year 2010 --end-year 2020

# Set logging level to debug
python -m src.scripts.historical_data_collection --log-level debug
```

### Programmatic Usage
```python
import asyncio
from src.scripts.historical_data_collection import collect_historical_data

# Collect data for a specific range
async def main():
    await collect_historical_data(
        start_year=2010,
        end_year=2020,
        data_dir="data",
        log_level="info"
    )

asyncio.run(main())
```

## Data Flow
1. `HistoricalDataCollector` initializes the collection pipeline and data cleaner
2. For each season, the collector:
   - Collects raw games, teams, and game details using `CollectionPipeline`
   - Cleans and validates the data using `DataCleaner`
   - Stores cleaned data in Parquet format
   - Generates and stores quality reports
3. After processing all seasons, a comprehensive progress report is generated

## Output Structure
```
data/
├── seasons/          # Raw data collected from ESPN
│   ├── 2000/
│   │   ├── games.parquet
│   │   ├── teams.parquet
│   │   └── game_details.parquet
│   └── ...
├── cleaned/          # Cleaned data after validation
│   ├── 2000/
│   │   ├── games_cleaned.parquet
│   │   └── quality_report.json
│   └── ...
└── reports/          # Overall collection reports
    └── collection_report_20230101_120000.json
```

## Progress Reports
The collection process generates detailed progress reports that include:
- Number of games and teams collected per season
- Collection status for each season
- Data quality issues identified
- Overall collection statistics

Example report:
```json
{
  "timestamp": "2023-01-01T12:00:00.000000",
  "seasons": [
    {
      "year": 2000,
      "games_count": 5000,
      "teams_count": 350,
      "data_issues": [
        "Column 'score' has 5 missing values"
      ],
      "status": "SUCCESS"
    },
    ...
  ],
  "total_games": 125000,
  "total_teams": 350,
  "total_seasons": 25,
  "total_issues": 120
}
```

## Configuration
The script behavior can be configured through command-line arguments:

| Argument | Description | Default |
|----------|-------------|---------|
| `--start-year` | First season year to collect | 2000 |
| `--end-year` | Last season year to collect | 2025 |
| `--data-dir` | Directory for storing collected data | "data" |
| `--log-level` | Logging level (debug, info, warning, error) | "info" |

## Error Handling
The script includes robust error handling:
- API failures for individual dates/games do not stop the entire process
- Failed collections are documented in the progress report
- Detailed logging helps identify and troubleshoot issues
- The script can be resumed if interrupted

## Performance Considerations
- Collection is time-consuming due to API rate limits (expect several hours for 25 seasons)
- The script respects ESPN's rate limits to avoid being blocked
- Data is saved incrementally, so progress is not lost if the script is interrupted
- For faster collection, consider collecting smaller ranges of seasons in parallel

## Data Quality Assurance
The script automatically:
- Identifies missing and invalid values
- Provides recommendations for data cleaning
- Applies common fixes (filling nulls, replacing empty strings, clipping values)
- Generates detailed quality reports for each season 