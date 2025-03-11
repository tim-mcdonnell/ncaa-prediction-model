# Code Standards

This document outlines the coding standards and best practices for the NCAA Basketball Prediction Model project. Following these standards ensures code consistency, maintainability, and quality.

## Python Style Guide

We follow a modified version of [PEP 8](https://www.python.org/dev/peps/pep-0008/) with enforcement through `ruff`.

### Key Style Points

- **Line Length**: Maximum 88 characters (Black's default)
- **Indentation**: 4 spaces (no tabs)
- **Naming Conventions**:
  - `snake_case` for variables, functions, and methods
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Quotes**: Double quotes (`"`) for strings, except when the string contains double quotes
- **Docstrings**: Google style

## Code Quality Tools

### Ruff for Linting and Formatting

We use [ruff](https://github.com/astral-sh/ruff) for both linting and formatting. Run these commands before submitting a PR:

```bash
# Run linting
ruff check .

# Apply formatting
ruff format .
```

Our ruff configuration checks for:

- Code style (`E` - pycodestyle errors)
- Logical errors (`F` - pyflakes)
- Best practices (`B` - flake8-bugbear)
- Import sorting (`I` - isort)

### MyPy for Type Checking

We use type hints throughout the codebase and enforce them with MyPy:

```bash
mypy .
```

## Documentation Standards

### Docstrings

Use Google-style docstrings for all public functions, classes, and methods:

```python
def calculate_team_rating(team_id: str, games: list[Game]) -> float:
    """Calculate a team's rating based on historical game data.
    
    This function implements the Elo rating system to quantify team strength
    based on win/loss history and opponent strength.
    
    Args:
        team_id: The unique identifier for the team.
        games: List of Game objects representing historical games.
        
    Returns:
        A float representing the team's rating.
        
    Raises:
        ValueError: If team_id is not found in any game.
    """
    # Implementation...
```

### Comments

- Use comments sparingly and focus on "why" not "what"
- Complex logic should be documented with clear comments
- Keep comments up-to-date with code changes

## Project Structure

### Module Organization

- Keep modules focused on a single responsibility
- Use meaningful directory names that reflect the module's purpose
- Follow the project structure outlined in the README

### Imports

- Group imports in the following order:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports
- Sort imports alphabetically within each group
- Use absolute imports for clarity

Example:
```python
# Standard library
import json
from datetime import datetime
from typing import Dict, List, Optional

# Third-party libraries
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Local application
from src.data.models import Game, Team
from src.features.transformers import TeamFeatureTransformer
```

## Testing Standards

### Test Structure

- Use pytest for all tests
- Organize tests to mirror the package structure
- Name test files with `test_` prefix

### Test Coverage

- Aim for at least 80% test coverage
- All critical paths should have tests
- Include edge cases and error conditions

### Test Quality

- Each test should test a single behavior
- Use descriptive test names that explain what's being tested
- Use fixtures to reduce test code duplication

Example:
```python
def test_team_rating_calculation_with_wins_and_losses():
    """Test that team ratings increase with wins and decrease with losses."""
    # Test implementation...
```

## Version Control

### Commit Messages

Follow the commit message format specified in the [Contributing Guide](contributing.md).

### Pull Requests

- Keep PRs focused on a single change
- Include tests for new features or bug fixes
- Update documentation for API changes

## Performance Considerations

- Profile code for performance bottlenecks
- Use vectorized operations (NumPy, Pandas) where applicable
- Be mindful of memory usage with large datasets
- Add caching for expensive operations

By following these standards, we ensure the codebase remains clean, maintainable, and high-quality. 