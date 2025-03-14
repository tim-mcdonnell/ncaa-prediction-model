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

## Pipeline Architecture

The project implements a modular pipeline architecture that orchestrates the flow from data collection to prediction:

```mermaid
graph TD
    A[Collection Pipeline] -->|Raw Data| B[Processing Pipeline]
    B -->|Processed Data| C[Feature Pipeline]
    C -->|Features| D[Model Training]
    D -->|Trained Models| E[Prediction Pipeline]
    E -->|Predictions| F[Visualization]
    
    G[Daily Update Pipeline] --> A
    G --> B
    G --> C
    G --> E
```

Key benefits of this architecture:
- **Incremental Processing**: Efficiently update only what has changed
- **Dependency Management**: Features are calculated in the correct order
- **Simple CLI**: Command-line interface for running pipelines

## Quick Start

### Setup
```bash
# Clone the repository
git clone https://github.com/tim-mcdonnell/ncaa-prediction-model.git
cd ncaa-prediction-model

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

### Basic Usage
```bash
# Run the complete end-to-end pipeline
python -m src.run all

# Run data collection for the current season
python -m src.run collect

# Run daily update (during basketball season)
python -m src.run daily
```

For more detailed information, see the [full documentation](https://tim-mcdonnell.github.io/ncaa-prediction-model/).

## Project Structure
The project follows a modular structure with clear separation of concerns:

```
ncaa-prediction-model/
├── data/                  # Data organized by processing stage
├── src/                   # Source code
│   ├── data/              # Data collection and processing
│   ├── features/          # Feature engineering
│   ├── models/            # ML models
│   ├── pipelines/         # Pipeline orchestration
│   └── visualization/     # Dashboard and visualization code
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
└── configs/               # Configuration files
```

## Project Milestones
The project is organized into 7 key milestones:

1. **Data Collection and Storage** - 🔄 In Progress
2. **Data Validation and Quality Control** - ⏱️ Not Started
3. **Feature Engineering** - ⏱️ Not Started
4. **Model Development** - ⏱️ Not Started
5. **Backtesting Framework** - ⏱️ Not Started
6. **Visualization and Dashboard** - ⏱️ Not Started
7. **Deployment and Monitoring** - ⏱️ Not Started

For detailed information on each milestone, see the [GitHub milestones page](https://github.com/tim-mcdonnell/ncaa-prediction-model/milestones).

## Development Approach

This project follows a Test-Driven Development (TDD) approach:
1. Write tests that define expected behavior before implementation
2. Implement the minimal code needed to pass tests
3. Refactor for clarity and efficiency while maintaining test coverage

## License
[MIT License](LICENSE)