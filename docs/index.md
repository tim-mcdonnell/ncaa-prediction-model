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

This documentation site provides comprehensive information about the project, organized into these sections:

### Documentation Sections

- [**Architecture**](architecture.md) - System design and component overview
- [**Development Guides**](development/setup.md) - Setup, workflow, and contribution guidelines
- [**Components**](components/data_collection.md) - Documentation for major system components
- [**How-to Guides**](guides/adding_features.md) - Task-oriented guides for common operations
  - [Adding Features](guides/adding_features.md) - How to add new basketball metrics
  - [Extending Pipelines](guides/extending_pipelines.md) - How to extend the pipeline framework
- [**Configuration**](components/pipeline_framework.md) - Configuration options for system components
- [**API Reference**](development/api-docs.md) - API documentation for the codebase

## Getting Started

To get started with the project:

```bash
# Clone the repository
git clone https://github.com/tim-mcdonnell/ncaa-prediction-model.git
cd ncaa-prediction-model

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

For detailed setup instructions, see the [Development Setup Guide](development/setup.md).

## Development Approach

We follow a Test-Driven Development (TDD) approach with these core principles:

1. **Tests First**: Write tests before implementing functionality to define expected behavior
2. **Minimal Implementation**: Write only enough code to pass the current tests
3. **Continuous Refactoring**: Improve code design after tests pass without changing behavior
4. **Documentation Alongside**: Document code and designs as part of the development cycle

For more details on our development workflow, see the [Development Workflow Guide](development/workflow.md).

## System Architecture

The system uses a pipeline architecture with modular components:

```
Collection Pipeline → Processing Pipeline → Feature Pipeline → Prediction Pipeline
                                                     ↓
                                          Daily Update Pipeline
```

For more details on the system architecture, see the [Architecture Documentation](architecture.md). 