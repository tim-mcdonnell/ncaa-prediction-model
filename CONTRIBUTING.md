---
title: Contributing Guidelines
description: Reference guide for the NCAA Basketball Analytics Project
---

# Contributing to NCAA Basketball Analytics Project

[TOC]

This document provides reference information for the NCAA Basketball Analytics Project. The project implements a medallion data architecture (Bronze/Silver/Gold) and follows Test-Driven Development (TDD) practices.

## Data Architecture

The project uses a three-tier medallion architecture for data processing:

!!! info "Medallion Architecture Layers"
    - **Bronze**: Raw data preserved in its original form with no transformations
    - **Silver**: Cleansed, validated data with consistent schema and quality checks
    - **Gold**: Business-ready analytics, aggregated datasets, and derived metrics

See [Architecture Documentation](docs/architecture/index.md) for detailed diagrams and implementation specifications.

## Development Workflow

The development process follows these sequential steps:

1. Review issue descriptions and relevant architecture documents
2. Create tests that define expected behavior before implementation
3. Implement minimal code to make tests pass successfully
4. Refactor for improved design while maintaining passing tests
5. Update documentation with complete function docstrings
6. Submit code for review with test coverage report

## Test-Driven Development Reference

!!! tip "TDD Cycle"
    1. **RED**: Create a failing test for the required behavior
    2. **GREEN**: Write minimal code to make the test pass
    3. **REFACTOR**: Improve code structure without changing behavior

### Test Structure Pattern

Structure test names using this descriptive convention:

```python
test_[WhatIsTested]_[UnderWhatConditions]_[WithWhatExpectedResult]
```

!!! example "Test Naming Examples"
    - `test_calculate_team_stats_with_valid_id_returns_complete_dictionary`
    - `test_process_game_data_with_missing_score_raises_validation_error`

### Test Implementation Pattern

Follow the Arrange-Act-Assert pattern for all tests:

```python
def test_calculate_win_percentage_with_two_wins_one_loss_returns_correct_value():
    # Arrange
    processor = TeamStatisticsProcessor()
    test_data = [
        {"game_id": 1, "result": "W"},
        {"game_id": 2, "result": "W"},
        {"game_id": 3, "result": "L"}
    ]

    # Act
    win_percentage = processor.calculate_win_percentage(test_data)

    # Assert
    assert win_percentage == 0.667  # 2/3 ≈ 0.667
```

### Effective Test Development

For the RED phase:

- Start with the simplest, most fundamental test case
- Verify the test fails for the expected reason
- Focus each test on a single specific behavior

For the GREEN phase:

- Write the minimal implementation to make the test pass
- Focus on functionality explicitly covered by tests
- Run all tests to verify no regressions

For the REFACTOR phase:

- Improve code organization while maintaining behavior
- Eliminate duplication and enhance naming
- Run tests after each refactoring change

## Configuration Standards

Store all configuration in YAML files instead of hardcoding values:

```python
# Loading configuration
with open("config/processing.yaml") as f:
    config = yaml.safe_load(f)
    
# Applying configuration
batch_size = config["processing"]["batch_size"]
```

See [Configuration README](config/README.md) for configuration structure details.

## Code Documentation Standards

### Function Documentation

Document all public functions using Google-style docstrings with type hints:

```python
def process_team_data(team_id: int, season: str) -> dict:
    """Process team data for the specified season.

    Args:
        team_id: The ESPN team ID
        season: The season in 'YYYY-YY' format

    Returns:
        Dictionary with processed team statistics

    Raises:
        ValueError: If team_id is invalid
        DataNotFoundError: If data for the season is not available
    """
```

### Module Documentation

Include module-level docstrings for all Python files:

```python
"""
Team statistics processing module.

This module handles the transformation of raw team data
from the bronze layer into validated silver layer data.
"""
```

## Data Processing Principles

### Data Preservation

!!! important "Bronze Layer Principles"
    For bronze layer data processing:
    - Maintain all original fields from source data
    - Preserve raw data format for audit purposes
    - Include metadata for tracking data lineage

### Incremental Processing

Design data pipelines to support:

- Full data refreshes for historical analysis
- Incremental updates for efficient processing

## Project Structure
