# NCAA Basketball Prediction Model

## Overview
This project develops a machine learning model to predict NCAA men's basketball game outcomes using 22 years of historical data. By analyzing team statistics, tournament performance, and other relevant factors, we create a data-driven approach to:

- Generate team rating metrics
- Calculate predicted point spreads (similar to Vegas lines)
- Predict total points (over/under)
- Determine win probability for each matchup

## Features
- **Data Collection**: Automated retrieval of historical data from ESPN API endpoints
- **Data Processing**: Cleaning, transformation, and feature engineering pipeline
- **Machine Learning**: Predictive modeling using team performance metrics
- **Visualization**: Interactive dashboard to explore underlying data, features, and model performance

## Tech Stack
- Python 3.11
- [uv](https://github.com/astral-sh/uv) for package management
- [ruff](https://github.com/astral-sh/ruff) for linting
- Data Analysis: Pandas, NumPy
- Machine Learning: Scikit-learn, TensorFlow/PyTorch
- Visualization: Plotly, Dash
- Data Storage: TBD (SQLite/PostgreSQL/MongoDB)

## Project Structure
```
ncaa-prediction-model/
├── data/                  # Raw and processed data
├── notebooks/             # Jupyter notebooks for exploration and analysis
├── src/                   # Source code
│   ├── data/              # Data collection and processing modules
│   ├── features/          # Feature engineering
│   ├── models/            # ML models
│   ├── visualization/     # Dashboard and visualization code
│   └── utils/             # Utility functions
├── tests/                 # Unit and integration tests
├── configs/               # Configuration files
├── docs/                  # Documentation
│   ├── milestones/        # Detailed milestone documentation
│   └── templates/         # Project templates
├── MILESTONES.md          # Project milestones and progress tracking
├── pyproject.toml         # Project dependencies and metadata
└── README.md              # Project documentation
```

## Project Milestones
The project is organized into 7 key milestones:

1. **Data Collection and Storage** - Gathering and storing historical NCAA basketball data
2. **Data Validation and Quality Control** - Ensuring data quality and completeness
3. **Feature Engineering** - Creating meaningful features from raw data
4. **Model Development** - Building and tuning prediction models
5. **Backtesting Framework** - Evaluating model performance on historical data
6. **Visualization and Dashboard** - Creating interfaces to explore data and predictions
7. **Deployment and Monitoring** - Deploying and maintaining the prediction system

For detailed information on each milestone, see [MILESTONES.md](MILESTONES.md) or the comprehensive documentation in the [docs/milestones](docs/milestones) directory.

## Project Templates
To maintain consistency throughout the project, we use a set of standardized templates:

- [Milestone Template](docs/templates/milestone_template.md) - For documenting project milestones
- [Task Template](docs/templates/task_template.md) - For defining specific implementation tasks
- [Issue Template](docs/templates/issue_template.md) - For tracking bugs and technical debt
- [PR Template](docs/templates/pr_template.md) - For code change submissions

For more information on using these templates, see the [templates documentation](docs/templates/README.md).

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
   
   # Install dependencies in development mode
   uv pip install -e ".[dev]"
   ```

4. Updating dependencies:
   ```bash
   # To update dependencies to their latest versions (within constraints)
   uv pip install -e ".[dev]" --upgrade
   ```

## Usage
Instructions for running the different components of the project will be added as they are developed.

## Data Sources
- ESPN API endpoints for historical NCAA basketball data
- Additional sources may be incorporated as needed

## License
[MIT License](LICENSE) 