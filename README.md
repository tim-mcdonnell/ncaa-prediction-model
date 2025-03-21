 NCAA Basketball Prediction Model

## Project Overview

This project builds predictive models for NCAA men's basketball games using historical data from ESPN's APIs. The system extracts, processes, and analyzes game statistics, team performance metrics, and other relevant data to generate predictions for future matchups.

## Key Features

- Data ingestion from ESPN APIs
- Historical game data processing via medallion architecture (Bronze → Silver → Gold)
- Feature engineering for predictive modeling
- Machine learning model training and evaluation
- Prediction generation for upcoming games

## Getting Started

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Clone the repository
git clone https://github.com/tim-mcdonnell/ncaa-prediction-model.git
cd ncaa-prediction-model

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
ncaa-prediction-model/
├── config/              # Configuration files
├── data/                # Data directory
│   ├── raw/             # Bronze layer - partitioned Parquet files
│   │   ├── scoreboard/  # Time-series data with year/month partitioning
│   │   │   ├── year=YYYY/month=MM/*.parquet
│   │   ├── teams/       # Reference data with appropriate partitioning
│   │   └── ...          # Other API endpoints with suitable partitioning
│   ├── ncaa.duckdb      # Database containing silver and gold layers
│   ├── predictions/     # Output predictions
│   └── models/          # Trained models
├── docs/                # Documentation
├── src/                 # Source code
│   ├── ingest/          # Data ingestion (Bronze)
│   ├── process/         # Data processing (Silver)
│   ├── features/        # Feature engineering (Gold)
│   ├── models/          # ML models
│   └── utils/           # Utilities
├── run.py               # Command-line interface
└── tests/               # Test suite
```

For detailed information on the data directory organization, see [Data Directory Structure](docs/architecture/data-directory-structure.md).

## Usage

```bash
# Ingest historical game data
python run.py ingest scoreboard --seasons 2022-23

# Process raw data to silver layer
python run.py process bronze-to-silver --entity games

# Generate features
python run.py features generate --feature-set team_performance

# Train prediction model
python run.py model train --model-type logistic --feature-set team_performance

# Generate predictions
python run.py model predict --upcoming
```

For a complete list of commands and options, see [CLI Design](docs/architecture/cli-design.md).

## Development Roadmap

1. **MVP (Current)**: Basic data pipeline with initial prediction model
2. **Phase 2**: Enhanced features and improved model accuracy
3. **Phase 3**: Web interface and automated predictions

See [Development Phases](docs/architecture/development-phases.md) for detailed information.

## Documentation

- [Architecture Overview](docs/architecture/index.md)
- [Data Pipeline](docs/architecture/data-pipeline.md)
- [Data Entities](docs/architecture/data-entities.md)
- [Configuration Management](docs/architecture/configuration-management.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## License

[MIT License](LICENSE)
