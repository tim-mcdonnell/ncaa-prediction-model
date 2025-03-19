# Contributing to NCAA Basketball Prediction Model

Thank you for your interest in contributing to the NCAA Basketball Prediction Model. This document provides guidelines to help both human contributors and AI coding agents successfully participate in this project.

## Table of Contents
- [Project Architecture](#project-architecture)
- [Development Process](#development-process)
  - [Test-Driven Development (TDD)](#test-driven-development-tdd)
  - [Development Workflow](#development-workflow)
  - [MVP Focus Areas](#mvp-focus-areas)
- [Code Standards](#code-standards)
  - [Quality Requirements](#quality-requirements)
  - [Style Guidelines](#style-guidelines)
  - [Documentation Requirements](#documentation-requirements)
- [Project Tools and Setup](#project-tools-and-setup)
  - [Development Environment](#development-environment)
  - [Command Line Interface](#command-line-interface)
  - [Configuration and Logging](#configuration-and-logging)
- [Data Processing Guidelines](#data-processing-guidelines)
- [Contribution Process](#contribution-process)
- [Additional Resources](#additional-resources)

## Project Architecture

This project implements a medallion data architecture with three distinct processing layers:

- **Bronze**: Raw data captured from ESPN APIs preserved in its original form
- **Silver**: Cleansed data with consistent schema and validation applied
- **Gold**: Feature-engineered datasets ready for model consumption

All data is stored in a single DuckDB database with consistent naming conventions:
- Bronze layer tables: `bronze_{api_endpoint_name}`
- Silver layer tables: `silver_{entity_name}`
- Gold layer tables: `gold_{feature_set_name}`

For detailed implementation specifics, refer to:
- [Architecture Overview](docs/architecture/index.md)
- [Data Pipeline](docs/architecture/data-pipeline.md)
- [Data Directory Structure](docs/architecture/data-directory-structure.md)
- [Data Entities](docs/architecture/data-entities.md)

## Development Process

### Test-Driven Development (TDD)

**⚠️ CRITICAL: This project strictly follows Test-Driven Development practices ⚠️**

For all functionality, implement the TDD "Red-Green-Refactor" cycle:

1. **RED**: Write a failing test that defines expected behavior
   - Test must fail initially to prove it can detect issues
   - Tests should be self-documenting with clear arrange-act-assert sections

2. **GREEN**: Implement minimal code to make the test pass
   - Focus on the simplest solution that works
   - Don't optimize prematurely
   - Ensure all tests now pass

3. **REFACTOR**: Improve the code while maintaining passing tests
   - Improve structure, naming, and performance
   - Verify tests remain green after each change
   - Ensure code follows project standards

When bugs are discovered:
- First write a test that reproduces the issue
- Fix the bug so the test passes
- Ensure all other tests still pass

For test structure, all tests must:
- Be independent and isolated from each other
- Include clear arrange-act-assert sections
- Cover edge cases and failure scenarios
- Have descriptive names following `test_[function]_[condition]_[expected_result]` pattern

Example test:
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

### Development Workflow

For each contribution, follow this workflow:

1. **Select Task**: Choose an issue from the project board
2. **Design**: Review architecture docs and plan your approach
3. **Test First**: Write tests defining expected behavior
4. **Implement**: Create minimal code to pass tests
5. **Refactor**: Improve code while maintaining test coverage
6. **Document**: Add clear docstrings and comments
7. **Submit**: Create a pull request with tests and docs

### MVP Focus Areas

For the initial MVP, prioritize these areas:

1. Building the core data pipeline (ESPN → Bronze → Silver)
2. Implementing basic team and game statistics processing
3. Creating essential features for the prediction model
4. Developing a simple but effective ML model

Future phases will expand on these foundations with advanced features and models.

## Code Standards

### Quality Requirements

**⚠️ CRITICAL: All code must pass automated quality checks ⚠️**

This project uses pre-commit hooks to enforce:

1. **Linting**: All code must pass `ruff` linting with NO warnings or errors
2. **Formatting**: All code must be formatted with `ruff format`
3. **Type Checking**: All code must pass `mypy` type checking
4. **Tests**: All tests must pass with no warnings or errors

**STRICTLY FORBIDDEN actions**:
- Using `git commit --no-verify` to bypass pre-commit hooks
- Modifying linting rules in `pyproject.toml` to silence errors
- Changing the pre-commit configuration to weaken checks
- Adding type-checking exceptions without team discussion and approval
- Using `# noqa` or similar directives to ignore linting errors

These rules apply to all contributors, including AI coding agents.

### Style Guidelines

Use these style conventions for all code:

- Follow PEP 8 conventions
- Use Google-style docstrings with type hints
- Follow consistent naming patterns
- Keep functions focused and single-purpose

### Documentation Requirements

Document all code with:

- Google-style docstrings for all public functions and classes
- Type hints for all parameters and return values
- Clear descriptions of purpose, parameters, returns, and exceptions

Example:
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

## Project Tools and Setup

### Development Environment

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

### Command Line Interface

The project provides a CLI for all operations following this pattern:

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

See [CLI Design](docs/architecture/cli-design.md) for complete documentation.

### Configuration and Logging

For system configuration:
- Use the provided configuration system for all settings
- Never hardcode values in application code
- Follow the [Configuration Management](docs/architecture/configuration-management.md) guidelines

For logging:
- Use structured logging as described in [Logging Strategy](docs/architecture/logging-strategy.md)
- Always include relevant context in log entries (IDs, operation types, etc.)

## Data Processing Guidelines

When working with data, follow these principles:

- Preserve all raw data in the bronze layer
- Include data provenance metadata (source, timestamp)
- Implement robust error handling for API failures
- Build incremental processing capabilities

For detailed implementation guidelines, see the [Data Pipeline](docs/architecture/data-pipeline.md) documentation.

## Contribution Process

When submitting changes:

1. Ensure all tests pass
2. Include relevant documentation updates
3. Provide a clear description of changes
4. Link to related issues
5. Request review from at least one maintainer

## Additional Resources

- [Architecture Overview](docs/architecture/index.md)
- [Data Pipeline](docs/architecture/data-pipeline.md)
- [Data Directory Structure](docs/architecture/data-directory-structure.md)
- [Data Entities](docs/architecture/data-entities.md)
- [Configuration Management](docs/architecture/configuration-management.md)
- [Logging Strategy](docs/architecture/logging-strategy.md)
- [CLI Design](docs/architecture/cli-design.md)
