# Contributing to NCAA Basketball Prediction Model

Thank you for your interest in contributing to the NCAA Basketball Prediction Model. This document provides guidelines to help you get started.

## Project Architecture

The project follows a medallion data architecture with three processing layers:

- **Bronze**: Raw data from ESPN APIs preserved in original form
- **Silver**: Cleansed data with consistent schema and validation 
- **Gold**: Feature-engineered datasets ready for model consumption

All data is stored in a single DuckDB database with tables following consistent naming conventions:
- Bronze layer: `bronze_{api_endpoint_name}`
- Silver layer: `silver_{entity_name}`
- Gold layer: `gold_{feature_set_name}`

For implementation details, see our architecture documentation:
- [Architecture Overview](docs/architecture/index.md)
- [Data Pipeline](docs/architecture/data-pipeline.md)
- [Data Directory Structure](docs/architecture/data-directory-structure.md)
- [Data Entities](docs/architecture/data-entities.md)

## MVP Development Focus

For the initial MVP, focus on:

1. Building the core data pipeline (ESPN → Bronze → Silver)
2. Implementing basic team and game statistics processing
3. Creating essential features for the prediction model
4. Developing a simple but effective ML model

Future phases will expand on these foundations with advanced features and models.

## Development Setup

1. Install `uv` according to [uv documentation](https://github.com/astral-sh/uv)
2. Clone the repository
3. Set up the development environment:
   ```bash
   # Create and activate virtual environment
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install development dependencies
   uv pip install -e ".[dev]"
   
   # Install pre-commit hooks
   pre-commit install
   ```

## Code Quality Standards

This project uses pre-commit hooks to enforce strict code quality standards:

1. **Linting**: All code must pass `ruff` linting with NO warnings or errors
2. **Formatting**: All code must be formatted with `ruff format`
3. **Type Checking**: All code must pass `mypy` type checking
4. **Tests**: All tests must pass with no warnings or errors

### ⚠️ IMPORTANT: Pre-commit Enforcement ⚠️

**NEVER bypass pre-commit hooks** by using `--no-verify` or similar flags. The following actions are **STRICTLY FORBIDDEN**:

- Using `git commit --no-verify` to bypass pre-commit hooks
- Modifying linting rules in `pyproject.toml` to silence errors
- Changing the pre-commit configuration to weaken checks
- Adding type-checking exceptions without team discussion and approval
- Using `# noqa` or similar directives to ignore linting errors

These rules apply to all contributors, including AI coding agents.

## Development Workflow

1. **Select Task**: Choose an issue from the project board
2. **Design**: Review architecture docs and plan your approach
3. **Test First**: Write tests defining expected behavior
4. **Implement**: Create minimal code to pass tests
5. **Refactor**: Improve code while maintaining test coverage
6. **Document**: Add clear docstrings and comments
7. **Submit**: Create a pull request with tests and docs

## Testing Guidelines

Follow test-driven development practices with descriptive test names:

```python
def test_calculate_win_percentage_with_valid_games_returns_correct_percentage():
    # Arrange: Set up test data
    games = [
        {"game_id": "1", "home_team": "Duke", "away_team": "UNC", "home_score": 75, "away_score": 70},
        {"game_id": "2", "home_team": "Duke", "away_team": "Virginia", "home_score": 65, "away_score": 70}
    ]
    team_id = "Duke"
    
    # Act: Call the function
    win_percentage = calculate_win_percentage(team_id, games)
    
    # Assert: Verify results
    assert win_percentage == 0.5  # 1 win, 1 loss = 50%
```

Name tests descriptively: `test_[function]_[condition]_[expected_result]`

## Code Style and Documentation

- Use Google-style docstrings with type hints
- Follow PEP 8 conventions
- Document all public functions and classes

```python
def get_team_stats(team_id: str, season: str) -> dict:
    """Retrieve team statistics for a specific season.
    
    Args:
        team_id: ESPN team identifier
        season: Season in YYYY-YY format (e.g., "2022-23")
        
    Returns:
        Dictionary of team statistics
        
    Raises:
        ValueError: If team_id or season is invalid
    """
```

## Configuration and Logging

- Use the provided configuration system for all settings - never hardcode values
- Follow the [Configuration Management](docs/architecture/configuration-management.md) guidelines
- Use structured logging as described in [Logging Strategy](docs/architecture/logging-strategy.md)
- Always include relevant context in log entries (IDs, operation types, etc.)

## Command Line Interface

The project provides a command-line interface (CLI) for all operations. The CLI follows a consistent pattern:

```bash
python run.py <command> <subcommand> [options]
```

Examples:
```bash
# Ingest scoreboard data for a specific date
python run.py ingest scoreboard --date 2023-03-15

# Process bronze data to silver layer
python run.py process bronze-to-silver --entity teams
```

See [CLI Design](docs/architecture/cli-design.md) for complete documentation of available commands and options.

## Data Processing Guidelines

- Preserve all raw data in the bronze layer
- Include data provenance metadata (source, timestamp)
- Implement robust error handling for API failures
- Build incremental processing capabilities

For detailed implementation guidelines, see the [Data Pipeline](docs/architecture/data-pipeline.md) documentation.

## Pull Request Process

1. Ensure all tests pass
2. Include relevant documentation updates
3. Provide a clear description of changes
4. Link to related issues
5. Request review from at least one maintainer
