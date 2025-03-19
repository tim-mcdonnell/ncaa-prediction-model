---
title: Command-Line Interface Design
description: Command-line interface design for the NCAA Basketball Prediction Model
---

# Command-Line Interface Design

[TOC]

This document outlines the command-line interface design for the NCAA Basketball Prediction Model, providing a consistent and intuitive way to interact with the application's functionality.

## Command Structure

The NCAA Basketball Prediction Model uses a simple Python script (`run.py`) at the project root for all operations. Commands follow a hierarchical structure with this pattern:

```
python run.py <command> <subcommand> [options]
```

Where:
- `<command>` is the primary operation category
- `<subcommand>` is the specific operation
- `[options]` are optional flags and parameters

## Implementation Details

The command interface is implemented using [Click](https://click.palletsprojects.com/), which provides:

1. **Composability**: Easy to compose complex command hierarchies
2. **Type Safety**: Automatic type conversion and validation 
3. **Self-Documentation**: Automatic help text generation
4. **Testability**: Easy to test commands

The main script (`run.py`) handles:
- Command-line argument parsing
- Loading configuration
- Setting up logging
- Executing the appropriate functionality
- Error handling and exit codes

## Code Organization

The CLI implementation follows this structure:

```
ncaa-prediction-model/
├── run.py                 # Main CLI entry point
└── src/                   # Source code
    ├── ingest/            # Data ingestion commands
    │   ├── __init__.py
    │   ├── scoreboard.py  # Scoreboard ingestion implementation
    │   └── teams.py       # Teams ingestion implementation
    ├── process/           # Data processing commands
    ├── features/          # Feature engineering commands 
    ├── models/            # Model training/prediction commands
    └── utils/             # Shared utilities
        ├── __init__.py
        ├── config.py      # Configuration management
        └── logging.py     # Logging setup
```

The `run.py` script imports functionality directly from the modules in `src/`:

```python
# Example import in run.py
from utils.config import get_config
from utils.logging import configure_logging
from ingest.scoreboard import ingest_scoreboard
```

## Command Categories

### 1. Data Ingestion Commands

Commands for fetching data from external sources:

```
python run.py ingest scoreboard [--date YYYY-MM-DD] [--seasons YYYY-YY]
python run.py ingest teams [--conference CONF] [--seasons YYYY-YY]
python run.py ingest games [--team-id TEAM_ID] [--seasons YYYY-YY]
```

### 2. Data Processing Commands

Commands for transforming data through the medallion layers:

```
python run.py process bronze-to-silver --entity ENTITY [--incremental]
python run.py process silver-to-gold --feature-set FEATURE_SET [--incremental]
```

### 3. Feature Engineering Commands

Commands for generating and managing features:

```
python run.py features generate --feature-set FEATURE_SET
python run.py features list [--entity ENTITY]
python run.py features analyze --feature FEATURE [--plot]
```

### 4. Model Commands

Commands for training, evaluating, and using models:

```
python run.py model train --model-type MODEL_TYPE --feature-set FEATURE_SET
python run.py model evaluate --model-id MODEL_ID [--test-set TEST_SET]
python run.py model predict --model-id MODEL_ID [--upcoming] [--date YYYY-MM-DD]
```

### 5. Utility Commands

Commands for system maintenance and information:

```
python run.py utils info [--verbose]
python run.py utils cleanup [--older-than DAYS]
python run.py utils validate [--config] [--data]
```

## Common Option Patterns

The interface uses consistent option patterns:

1. **Date Options**: `--date YYYY-MM-DD` for date-specific operations
2. **Range Options**: `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` for date ranges
3. **Filter Options**: `--entity`, `--conference`, etc. for filtering
4. **Output Options**: `--format [json|csv|table]` for output formatting
5. **Behavioral Options**: `--verbose`, `--dry-run`, `--force` for behavior modification

## Consistent Return Values

Commands follow consistent exit code patterns:

- `0`: Success
- `1`: User error (bad input, etc.)
- `2`: System error (IO error, network error, etc.)

## Documentation

Help text is automatically generated from docstrings and option descriptions:

```bash
$ python run.py --help
Usage: run.py [OPTIONS] COMMAND [ARGS]...

  NCAA Basketball Prediction Model.
  
  Run commands for data ingestion, processing, model training, and more.

Options:
  --log-level TEXT      Override logging level
  --config-dir TEXT     Configuration directory
  --help                Show this message and exit.

Commands:
  features  Commands for feature engineering.
  ingest    Commands for data ingestion.
  model     Commands for model operations.
  process   Commands for data processing.
  utils     Utility commands.
```

More detailed help is available for each command and subcommand:

```bash
$ python run.py ingest scoreboard --help
Usage: run.py ingest scoreboard [OPTIONS]

  Ingest scoreboard data from ESPN API.

Options:
  --date [%Y-%m-%d]  Date to fetch scoreboard data for (YYYY-MM-DD)
  --seasons TEXT     Comma-separated list of seasons (YYYY-YY)
  --help             Show this message and exit.
```

## Testing Commands

Commands can be tested using Click's testing utilities:

```python
from click.testing import CliRunner
from run import cli

def test_scoreboard_ingestion():
    runner = CliRunner()
    result = runner.invoke(cli, ["ingest", "scoreboard", "--date", "2023-03-15"])
    assert result.exit_code == 0
    assert "Scoreboard ingestion completed successfully" in result.output
``` 