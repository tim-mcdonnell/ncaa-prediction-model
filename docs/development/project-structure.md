# Project Structure

This document provides an overview of the NCAA Basketball Prediction Model project structure, explaining the purpose and organization of each directory and key file.

## Root Directory

The root directory contains configuration files and top-level directories:

```
ncaa-prediction-model/
├── .github/                      # GitHub configuration, workflows
├── .venv/                        # Virtual environment
├── configs/                      # Configuration files
├── data/                         # Data storage
├── docs/                         # Documentation
├── logs/                         # Log files
├── notebooks/                    # Jupyter notebooks
├── scripts/                      # Utility scripts
├── site/                         # Generated mkdocs site
├── src/                          # Source code
├── tests/                        # Test suite
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── .python-version               # Python version specifier
├── LICENSE                       # License file
├── mkdocs.yml                    # MkDocs configuration
├── pyproject.toml                # Project configuration
├── README.md                     # Project readme
└── uv.lock                       # Dependency lock file
```

## Configuration Files

Key configuration files in the root directory:

- **pyproject.toml**: Package definition, dependencies, and tool configuration
- **mkdocs.yml**: Documentation site configuration
- **.env.example**: Template for environment variables
- **.python-version**: Python version specifier for tools like pyenv

## `src/` Directory

The source code has been reorganized to simplify abstractions and provide clearer boundaries:

```
src/
├── data/                         # Data handling
│   ├── collection/               # Data collection
│   │   ├── espn/                 # ESPN implementation
│   │   │   ├── client.py         # HTTP client for ESPN
│   │   │   ├── parsers.py        # Parse ESPN responses
│   │   │   └── models.py         # Data models for ESPN data
│   │   ├── connectors/           # HTTP connectors
│   │   └── extractors/           # Data extractors
│   ├── storage/                  # Data storage
│   │   ├── parquet_io.py         # Parquet read/write utilities
│   │   ├── schema.py             # Data schemas
│   │   └── validation.py         # Data validation
│   └── processing/               # Data processing
│       ├── transformations.py    # Data transformation functions
│       └── cleaning.py           # Data cleaning functions
├── features/                     # Feature engineering
│   ├── base.py                   # Base feature class
│   ├── pipeline.py               # Feature pipeline
│   ├── team_performance/         # Team performance features
│   ├── advanced_team/            # Advanced team metrics
│   ├── player_stats/             # Player statistics
│   └── composite/                # Composite features
├── models/                       # Model implementations
│   ├── base.py                   # Base model class
│   ├── evaluation/               # Model evaluation
│   ├── training/                 # Model training
│   └── prediction/               # Prediction generation
├── pipelines/                    # Pipeline orchestration
│   ├── collection_pipeline.py    # Orchestrates data collection
│   ├── feature_pipeline.py       # Orchestrates feature engineering
│   └── prediction_pipeline.py    # Orchestrates model prediction
├── visualization/                # Visualization components
│   ├── dashboards/               # Dashboard components
│   └── plots/                    # Plot generation
└── utils/                        # Utility functions
    ├── logging.py                # Logging setup
    ├── config/                   # Configuration management
    │   ├── base.py               # Base configuration handling
    │   ├── validation.py         # Configuration validation
    │   └── environment.py        # Environment-specific configuration
    ├── resilience/               # Resilience patterns
    │   ├── retry.py              # Retry mechanisms
    │   ├── circuit_breaker.py    # Circuit breaker pattern
    │   └── fallback.py           # Fallback strategies
    └── validation.py             # Data validation
```

### Data Module

The `data` module has been simplified:

1. **Collection**: Simplified to start with a direct ESPN implementation, while retaining the connectors and extractors for potential future expansion
2. **Storage**: Replaced the repository pattern with direct Parquet file operations
3. **Processing**: Added explicit data transformation and cleaning functions

Key components:
- `ESPNClient`: Direct client for ESPN APIs
- `parquet_io.py`: Utilities for reading and writing Parquet files
- `transformations.py`: Functions for transforming data between stages

### Features Module

The `features` module remains largely as before, implementing the feature engineering system defined in ADR-003:

- `Feature`: Base class for all feature calculators
- `FeaturePipeline`: Orchestrates feature calculation with dependency resolution
- Feature implementations organized by category (basic, advanced, etc.)

### Pipelines Module

A new `pipelines` module has been added to explicitly manage data flow between components:

- `collection_pipeline.py`: Manages collection from ESPN and storage to raw Parquet
- `feature_pipeline.py`: Manages data processing and feature engineering
- `prediction_pipeline.py`: Manages model prediction workflows

### Utils Module

The `utils` module has been expanded with better configuration and resilience patterns:

- `config/`: Enhanced configuration management
- `resilience/`: Explicit patterns for error handling and resilience
- `logging.py`: Centralized logging configuration
- `validation.py`: Data validation utilities

## `tests/` Directory

The test suite mirrors the updated structure of the source code:

```
tests/
├── conftest.py                   # pytest configuration
├── data/                         # Data module tests
│   ├── collection/               # Collection tests
│   │   ├── espn/                 # ESPN client tests
│   │   ├── connectors/           # Connector tests
│   │   └── extractors/           # Extractor tests
│   ├── storage/                  # Storage tests
│   └── processing/               # Processing tests
├── features/                     # Feature tests
├── models/                       # Model tests
├── pipelines/                    # Pipeline tests
├── integration/                  # Integration tests
│   └── end_to_end/               # End-to-end workflow tests
└── fixtures/                     # Test fixtures
    ├── espn_responses/           # Sample API responses
    ├── sample_data/              # Sample datasets
    └── expected_results/         # Expected test results
```

## `data/` Directory

The data directory structure has been updated to match ADR-004:

```
data/
├── raw/                          # Minimally transformed ESPN data
│   ├── games/
│   │   ├── 2022/
│   │   │   ├── games.parquet     # Basic game metadata 
│   │   │   ├── box_scores.parquet # Box score data
│   │   │   └── play_by_play.parquet # Play-by-play data
│   │   └── ...
│   ├── teams/
│   │   ├── teams.parquet         # Team information
│   │   └── rankings.parquet      # Team rankings
│   └── ...
├── processed/                    # Cleaned, validated, unified data
│   ├── games_unified.parquet     # Games with consistent schema across seasons
│   ├── team_seasons.parquet      # Team-season level data
│   └── player_games.parquet      # Player-game level data
└── features/                     # Engineered features
    ├── team_ratings.parquet      # Team performance metrics
    ├── game_features.parquet     # Feature matrix for game prediction
    └── tournament_features.parquet # Features specific to tournament play
```

## `configs/` Directory

Configuration files have been enhanced with validation schemas:

```
configs/
├── collection/                   # Data collection configs
│   ├── espn_endpoints.yml        # ESPN endpoint configuration
│   └── connectors.yml            # HTTP connector configuration
├── features/                     # Feature calculation configs
│   └── feature_sets.yml          # Feature set definitions
├── model/                        # Model configs
│   └── model_params.yml          # Model hyperparameters
└── schemas/                      # Configuration validation schemas
    ├── espn_config_schema.json   # JSON Schema for ESPN config
    └── feature_config_schema.json # JSON Schema for feature config
```

## Design Principles

The revised structure follows these key design principles:

1. **Progressive Abstraction**: Start with simpler, concrete implementations and abstract later as needed
2. **Data Flow Clarity**: Make data flow between components explicit through pipelines
3. **Functional Core**: Prefer pure functions for data transformations
4. **Resilient Design**: Make error handling and resilience explicit
5. **Validated Configuration**: Use schema validation for configurations
6. **Test-Driven Development**: Maintain comprehensive test coverage

## Implementation Notes

The revised architecture makes the following simplifications:

1. **Direct ESPN Client**: Start with a direct ESPN client implementation instead of complex plugin system
2. **Parquet-First Storage**: Use Parquet files directly without a database abstraction
3. **Explicit Pipelines**: Make data flow between components explicit through pipeline modules
4. **Configuration Validation**: Add schema validation for configuration files
5. **Resilience Patterns**: Make error handling and resilience patterns explicit 