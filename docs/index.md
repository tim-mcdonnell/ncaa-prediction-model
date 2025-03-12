# NCAA Basketball Prediction Model

![Basketball](https://source.unsplash.com/featured/1200x400/?basketball)

## Project Overview

This project develops a machine learning model to predict NCAA men's basketball game outcomes using 22 years of historical data. By analyzing team statistics, tournament performance, and other relevant factors, we create a data-driven approach to:

- Generate team rating metrics
- Calculate predicted point spreads (similar to Vegas lines)
- Predict total points (over/under)
- Determine win probability for each matchup

## Key Features

- **Data Collection**: Automated retrieval of historical data from ESPN API endpoints
- **Data Processing**: Cleaning, transformation, and feature engineering pipeline
- **Machine Learning**: Predictive modeling using team performance metrics
- **Visualization**: Interactive dashboard to explore underlying data, features, and model performance

## Project Structure

The project is organized into 7 key milestones:

1. **Data Collection and Storage** - Gathering and storing historical NCAA basketball data
2. **Data Validation and Quality Control** - Ensuring data quality and completeness
3. **Feature Engineering** - Creating meaningful features from raw data
4. **Model Development** - Building and tuning prediction models
5. **Backtesting Framework** - Evaluating model performance on historical data
6. **Visualization and Dashboard** - Creating interfaces to explore data and predictions
7. **Deployment and Monitoring** - Deploying and maintaining the prediction system

For detailed information on each milestone, see the [GitHub milestones page](https://github.com/tim-mcdonnell/ncaa-prediction-model/milestones).

## Documentation

This documentation site provides:

- Detailed project overview and architecture
- Milestone documentation with implementation details
- Development guides and code standards
- API reference for the codebase

### Documentation Sections

- [**Project Overview**](overview/index.md) - High-level project description and goals
- [**Architecture Documentation**](development/pipeline-architecture.md) - System design and architectural decisions
- [**Development Guides**](development/index.md) - Guidelines for contributing to the project
- [**API Reference**](reference/index.md) - API documentation for the codebase

## Getting Started

To get started with the project:

```bash
# Clone the repository
git clone https://github.com/yourusername/ncaa-prediction-model.git
cd ncaa-prediction-model

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
``` 