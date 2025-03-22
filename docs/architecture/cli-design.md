---
title: CLI Design
description: Command-line interface design for the NCAA Basketball Prediction Model
---

# Command-Line Interface Design

This document outlines the command-line interface (CLI) design for the NCAA Basketball Prediction Model.

## Command Structure

The CLI follows the structure:

```
python run.py <command> <subcommand> [options]
```

Where:
- `<command>` is the main category (e.g., `ingest`, `process`, `model`)
- `<subcommand>` is the specific action within that category
- `[options]` are parameters specific to the subcommand

## Implementation

The CLI is implemented using [Click](https://click.palletsprojects.com/), which provides:

1. **Composability**: Commands can be nested and combined
2. **Type Safety**: Automatic type conversion and validation
3. **Self-Documentation**: Help text generated automatically
4. **Testability**: Commands can be invoked programmatically in tests

## Command Categories

### Data Ingestion Commands

Ingestion commands use a unified approach based on configuration objects:

```
python run.py ingest [endpoint] [options]
```

Where `[endpoint]` can be:

#### Scoreboard Endpoint

```
python run.py ingest scoreboard [--date YYYY-MM-DD] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--seasons SEASON[,SEASON...]] [--today] [--yesterday] [--year YEAR] [--force-check] [--force-overwrite] [--concurrency N]
```

Options:
- `--date`: Single date to ingest (format: YYYY-MM-DD)
- `--start-date`/`--end-date`: Date range to ingest
- `--seasons`: Comma-separated list of seasons (e.g., "2022-23,2023-24")
- `--today`/`--yesterday`: Flags to ingest data for today or yesterday
- `--year`: Calendar year to ingest all dates
- `--force-check`: Force API checks even if data exists
- `--force-overwrite`: Force overwrite of existing data
- `--concurrency`: Number of concurrent requests (default: 5)

#### Teams Endpoint

```
python run.py ingest teams [--seasons SEASON[,SEASON...]] [--conference CONF] [--limit N] [--page N] [--force-check] [--force-overwrite] [--concurrency N]
```

Options:
- `--seasons`: Comma-separated list of seasons (e.g., "2022-23,2023-24")
- `--conference`: Filter by conference
- `--limit`: Items per page
- `--page`: Page number
- `--force-check`: Force API checks even if data exists
- `--force-overwrite`: Force overwrite of existing data
- `--concurrency`: Number of concurrent requests (default: 5)

#### Multiple Endpoints (Unified Ingestion)

```
python run.py ingest all [--endpoints ENDPOINT[,ENDPOINT...]] [--max-parallel N] [<endpoint-specific-options>]
```

Options:
- `--endpoints`: Comma-separated list of endpoints to ingest (e.g., "scoreboard,teams")
- `--max-parallel`: Maximum number of endpoints to process in parallel
- All options from individual endpoints are supported

### Data Processing Commands

```
python run.py process bronze-to-silver [--entity ENTITY] [--date YYYY-MM-DD] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--incremental]
```

Options:
- `--entity`: Entity to process (games, teams, etc.)
- `--date`: Single date to process
- `--start-date`/`--end-date`: Date range to process
- `--incremental`: Only process new records

### Feature Engineering Commands

```
python run.py features generate [--feature-set FEATURE_SET] [--season SEASON] [--date YYYY-MM-DD] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--lookback N]
```

Options:
- `--feature-set`: Feature set to generate
- `--season`: Season identifier
- `--date`: Date to generate features for
- `--start-date`/`--end-date`: Date range to generate features for
- `--lookback`: Number of games to consider for trailing metrics

### Model Commands

```
python run.py model train [--model-type MODEL_TYPE] [--feature-set FEATURE_SET] [--season SEASON] [--split-date YYYY-MM-DD] [--cv-folds N]
```

```
python run.py model predict [--model-id MODEL_ID] [--upcoming] [--date YYYY-MM-DD]
```

Options:
- `--model-type`: Type of model to train
- `--feature-set`: Feature set to use
- `--season`: Season to train/predict on
- `--split-date`: Date to split train/test data
- `--cv-folds`: Number of cross-validation folds
- `--model-id`: ID of trained model to use for prediction
- `--upcoming`: Flag to predict upcoming games

### Utility Commands

```
python run.py utils info [--verbose]
```

```
python run.py utils purge-cache [--entity ENTITY] [--confirm]
```

Options:
- `--verbose`: Show detailed information
- `--entity`: Specific entity to purge from cache
- `--confirm`: Skip confirmation prompt

## Common Option Patterns

1. **Date Selection**:
   - Single date (`--date`)
   - Date range (`--start-date` and `--end-date`)
   - Season (`--season`)
   - Special shortcuts (`--today`, `--yesterday`, `--year`)

2. **Processing Control**:
   - Force operations (`--force-check`, `--force-overwrite`)
   - Incremental processing (`--incremental`)
   - Concurrency control (`--concurrency`, `--max-parallel`)

3. **Output Control**:
   - Verbosity (`--verbose`)
   - Format (`--format`)

## Examples

1. Ingest scoreboard data for a specific date:
   ```
   python run.py ingest scoreboard --date 2023-03-15
   ```

2. Ingest teams data for the 2023-24 season:
   ```
   python run.py ingest teams --seasons 2023-24
   ```

3. Ingest multiple endpoints in one command:
   ```
   python run.py ingest all --endpoints scoreboard,teams --date 2023-03-15 --seasons 2023-24
   ```

4. Process bronze data to silver for games entity:
   ```
   python run.py process bronze-to-silver --entity games --start-date 2023-03-01 --end-date 2023-03-31
   ```

5. Generate team performance features:
   ```
   python run.py features generate --feature-set team_performance --season 2023-24
   ```

6. Train a prediction model:
   ```
   python run.py model train --model-type logistic --feature-set team_performance --season 2023-24
   ```

7. Make predictions for upcoming games:
   ```
   python run.py model predict --model-id logistic-20230501 --upcoming
   ```

## Return Values

All CLI commands return appropriate exit codes:
- `0`: Success
- `1`: Error (with appropriate error message)

For commands that create or modify data, a summary of changes is printed:
```
Successfully ingested scoreboard data:
  - Date: 2023-03-15
  - Games: 45
  - Storage path: data/raw/scoreboard/year=2023/month=03/scoreboard-2023-03-15.parquet
```

## Help Text

Help text is generated automatically from docstrings:

```
$ python run.py ingest scoreboard --help
Usage: run.py ingest scoreboard [OPTIONS]

  Ingest scoreboard data from ESPN API.

  This command fetches and stores raw scoreboard data for specified dates.
  Data is stored in the bronze layer as Parquet files.

Options:
  --date TEXT                     Single date to ingest (YYYY-MM-DD)
  --start-date TEXT               Start date for range (YYYY-MM-DD)
  --end-date TEXT                 End date for range (YYYY-MM-DD)
  --seasons TEXT                  Comma-separated list of seasons
  --today                         Ingest data for today
  --yesterday                     Ingest data for yesterday
  --year INTEGER                  Calendar year to ingest
  --force-check                   Force API checks even if data exists
  --force-overwrite               Force overwrite of existing data
  --concurrency INTEGER           Number of concurrent requests
  --help                          Show this message and exit.
```
