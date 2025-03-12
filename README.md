# NCAA Basketball Prediction Model

📚 **[View Full Documentation](https://tim-mcdonnell.github.io/ncaa-prediction-model/)**

## Overview
This project develops a machine learning model to predict NCAA men's basketball game outcomes using 22 years of historical data. By analyzing team statistics, tournament performance, and other relevant factors, we create a data-driven approach to:

- Generate team rating metrics
- Calculate predicted point spreads (similar to Vegas lines)
- Predict total points (over/under)
- Determine win probability for each matchup

## Features
- **Data Collection**: Automated retrieval of historical data from ESPN API endpoints
- **Data Processing**: Cleaning, transformation, and feature engineering pipeline
- **Feature Engineering**: Calculation of 60+ basketball metrics of varying complexity
- **Machine Learning**: Predictive modeling using team performance metrics
- **Pipeline Architecture**: End-to-end orchestration for incremental and full processing
- **Visualization**: Interactive dashboard to explore underlying data, features, and model performance

## Tech Stack
- Python 3.11
- [uv](https://github.com/astral-sh/uv) for package management
- [ruff](https://github.com/astral-sh/ruff) for linting
- Data Processing: Polars, Parquet
- Machine Learning: Scikit-learn, TensorFlow/PyTorch
- Visualization: Plotly, Dash
- Testing: pytest with TDD approach

## Project Structure
```
ncaa-prediction-model/
├── data/                  # Data organized by processing stage
│   ├── raw/               # Minimally transformed ESPN data
│   ├── processed/         # Cleaned, validated data
│   └── features/          # Engineered features
├── notebooks/             # Jupyter notebooks for exploration and analysis
├── src/                   # Source code
│   ├── data/              # Data collection and processing
│   │   ├── collection/    # ESPN API client and data fetching
│   │   ├── storage/       # Parquet I/O utilities
│   │   └── processing/    # Data transformation functions
│   ├── features/          # Feature engineering
│   │   ├── team_performance/ # Basic team metrics
│   │   ├── advanced_team/ # Advanced metrics
│   │   └── ...            # Other feature categories
│   ├── models/            # ML models
│   ├── pipelines/         # Pipeline orchestration
│   │   ├── base_pipeline.py      # Shared pipeline functionality
│   │   ├── collection_pipeline.py # Data collection orchestration
│   │   ├── processing_pipeline.py # Data processing orchestration
│   │   ├── feature_pipeline.py   # Feature engineering orchestration
│   │   ├── prediction_pipeline.py # Prediction orchestration
│   │   └── daily_update.py       # Combined daily update pipeline
│   ├── visualization/     # Dashboard and visualization code
│   └── utils/             # Utility functions
├── tests/                 # Unit and integration tests
├── configs/               # Configuration files
├── docs/                  # Documentation
│   ├── architecture/      # Architectural Decision Records
│   ├── development/       # Development guides
│   ├── milestones/        # Detailed milestone documentation
│   └── features/          # Feature documentation
├── pyproject.toml         # Project dependencies and metadata
└── README.md              # Project documentation
```

## Pipeline Architecture

The project implements a modular pipeline architecture that orchestrates the flow from data collection to prediction:

1. **Collection Pipeline**: Fetches data from ESPN APIs, with support for full historical or incremental daily updates
2. **Processing Pipeline**: Transforms raw data into standardized formats suitable for feature engineering
3. **Feature Pipeline**: Calculates 60+ basketball metrics with automatic dependency resolution
4. **Prediction Pipeline**: Generates predictions using the latest features and trained models
5. **Daily Update Pipeline**: Combines all pipelines for efficient daily updates during basketball season

Key benefits of this architecture:
- **Incremental Processing**: Efficiently update only what has changed (new/updated games)
- **Dependency Management**: Features are calculated in the correct order based on dependencies
- **Configuration Management**: Flexible configuration to control pipeline behavior
- **Error Handling**: Robust error handling and logging to prevent pipeline failures
- **Progress Tracking**: Clear progress reporting for long-running operations
- **Simple CLI**: Command-line interface for running pipelines without writing code

### Daily Updates

The architecture is specifically designed to support efficient daily updates during the basketball season:

```bash
# Run daily update (fetches new data, processes it, calculates features, generates predictions)
python -m src.run daily

# Run daily update for a specific date
python -m src.run daily --date="2024-03-15"

# Run daily update with specific feature recalculation
python -m src.run daily --ids="team_offensive_efficiency,team_defensive_efficiency"
```

The daily update pipeline:
1. Determines the current basketball season
2. Collects only new/updated games (incremental mode)
3. Processes new data and merges with existing processed data
4. Recalculates features affected by new data
5. Generates updated predictions

This approach ensures that the system stays current during the basketball season without rebuilding 22 years of historical data each time.

For more detailed information on the pipeline architecture, see [docs/development/pipeline-architecture.md](docs/development/pipeline-architecture.md).

## Project Milestones
The project is organized into 7 key milestones:

1. **Data Collection and Storage** - 🔄 In Progress
   - Gathering and storing historical NCAA basketball data
   
2. **Data Validation and Quality Control** - ⏱️ Not Started
   - Ensuring data quality and completeness
   
3. **Feature Engineering** - ⏱️ Not Started
   - Creating meaningful features from raw data
   
4. **Model Development** - ⏱️ Not Started
   - Building and tuning prediction models
   
5. **Backtesting Framework** - ⏱️ Not Started
   - Evaluating model performance on historical data
   
6. **Visualization and Dashboard** - ⏱️ Not Started
   - Creating interfaces to explore data and predictions
   
7. **Deployment and Monitoring** - ⏱️ Not Started
   - Deploying and maintaining the prediction system

For detailed information on each milestone, see the [GitHub milestones page](https://github.com/tim-mcdonnell/ncaa-prediction-model/milestones).

## Project Documentation Standards
To maintain consistency throughout the project, we follow a set of standardized examples:

- [Milestone Example](docs/examples/ai_milestone_example.md) - For documenting project milestones
- [AI Task Example](docs/examples/ai_task_example.md) - For defining implementation tasks for AI agents
- [Issue Example](docs/examples/ai_issue_example.md) - For tracking bugs and technical debt
- [PR Example](docs/examples/ai_pr_example.md) - For code change submissions

For more information on using these examples, see the [documentation standards](docs/examples/index.md).

## Setup
1. Clone this repository
2. Install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   # Create a virtual environment
   uv venv
   
   # Activate the virtual environment
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   uv pip install -e .
   ```

4. Updating dependencies:
   ```bash
   # To update dependencies to their latest versions (within constraints)
   uv pip install -e . --upgrade
   ```

## Usage

### Running the Pipeline

```bash
# Run the complete end-to-end pipeline
python -m src.run all

# Run only data collection for the current season
python -m src.run collect

# Run data collection for all historical seasons
python -m src.run collect --full

# Process raw data into standardized formats
python -m src.run process

# Calculate features
python -m src.run features

# Calculate specific features
python -m src.run features --ids="team_offensive_efficiency,team_defensive_efficiency"

# Generate predictions for upcoming games
python -m src.run predict

# Run daily update (during basketball season)
python -m src.run daily
```

## Data Sources
- ESPN API endpoints for historical NCAA basketball data
- Additional sources may be incorporated as needed

## License
[MIT License](LICENSE) 