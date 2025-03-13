# AI Coding Agent Guide

This guide provides essential information for AI coding agents working on the NCAA Basketball Prediction Model.

## Quick Reference

| **Category** | **Key Points** |
|--------------|----------------|
| **Development Approach** | Test-Driven Development (TDD): Tests first, minimal implementation, then refactor |
| **Project Structure** | Pipeline architecture, Parquet storage, `src/` for code, `tests/` mirroring code structure |
| **Package Management** | ✅ Use `uv` for dependencies ❌ NEVER use pip directly |
| **Data Processing** | ✅ Use Polars for all data manipulation ❌ NEVER use pandas |
| **Terminal Commands** | ✅ Use `tmp/` files for multiline content ❌ NEVER use newlines in commands |

## Key Documentation

- **[Test Strategy](./development/testing.md)**: Our TDD approach and testing practices
- **[Documentation Guide](./development/documentation.md)**: Documentation standards
- **[Architecture Overview](./architecture.md)**: System design and components

## TDD Workflow

1. **Red Phase:**
   - Write failing tests first
   - Document expected behavior in test docstrings
   
2. **Green Phase:**
   - Write minimal code to pass tests
   - Include proper docstrings
   
3. **Refactor Phase:**
   - Improve code without changing behavior
   - Document design decisions in comments

## Architecture Overview

Pipeline architecture with these core components:

```
Collection Pipeline → Processing Pipeline → Feature Pipeline → Prediction Pipeline
                                                      ↓
                                            Daily Update Pipeline
```

1. **Collection Pipeline**: Fetches ESPN API data
2. **Processing Pipeline**: Transforms raw data
3. **Feature Pipeline**: Calculates basketball metrics
4. **Prediction Pipeline**: Generates predictions
5. **Daily Update Pipeline**: Orchestrates daily updates

## Documentation Standards

- Document code alongside development (in the TDD cycle)
- Use Google-style docstrings for all public functions/classes
- Focus on practical information over theoretical explanations

Example docstring:
```python
def collect_game_data(season: int, game_ids: List[str] = None) -> pl.DataFrame:
    """
    Collect NCAA basketball game data from ESPN.
    
    Args:
        season: Basketball season year (e.g., 2023 for 2022-23 season)
        game_ids: Optional list of specific game IDs to collect
            
    Returns:
        DataFrame containing raw game data
    """
```

## ⚠️ Critical Terminal Command Limitations ⚠️

Terminal commands with newlines WILL FAIL. Always use temporary files:

```python
# ✅ CORRECT APPROACH
# 1. Create temporary file
edit_file("tmp/commit_msg.md", """Feature: Add functionality

- Add component
- Implement feature""")

# 2. Use in command
run_terminal_cmd("git commit -F tmp/commit_msg.md")

# 3. Clean up
delete_file("tmp/commit_msg.md")

# ❌ INCORRECT - Will fail
# run_terminal_cmd("""git commit -m "Feature: Add functionality
# 
# - Add component
# - Implement feature"""")
```

This pattern is REQUIRED for:
- Git commit messages
- GitHub PR descriptions and issue creation
- Any multiline command input

## Common Mistakes to Avoid

### Package Management

```python
# ✅ CORRECT
run_terminal_cmd("uv pip install -e .")
run_terminal_cmd("uv pip install new-package")

# ❌ INCORRECT
# run_terminal_cmd("pip install -e .")
```

### Data Processing

```python
# ✅ CORRECT
import polars as pl
df = pl.read_parquet("path/to/file.parquet")
result = df.filter(pl.col("column") > 0)

# ❌ INCORRECT
# import pandas as pd
# df = pd.read_parquet("path/to/file.parquet")
```

### Data Storage

```python
# ✅ CORRECT
from src.data.storage.parquet_io import save_parquet, load_parquet
df = load_parquet(data_category="raw", filename="games/2023/games")
save_parquet(df, data_category="processed", filename="games_unified")

# ❌ INCORRECT - Don't create custom database abstractions
```

## Checkpoint Requirements

Always get explicit confirmation before:
- Git operations (commits, pushes, branch creation)
- Adding new dependencies
- Creating new root folders
- Deviating from project architecture
- Integrating with external APIs

For routine code implementation, proceed without constant check-ins.

## Feature Implementation Example

```python
# Test first (Red phase)
def test_offensive_efficiency_calculation():
    """Test that offensive efficiency is calculated correctly as points per 100 possessions."""
    # Test implementation...

# Then implementation (Green phase)
class OffensiveEfficiencyFeature(Feature):
    id = "team_offensive_efficiency"
    name = "Team Offensive Efficiency"
    dependencies = ["team_possessions"]
    required_data = ["games", "teams"]
    
    def calculate(self, data: dict[str, pl.DataFrame]) -> pl.DataFrame:
        # Implementation using Polars
```

## Code Contribution Tips

1. **Follow TDD cycle** for all new code
2. **Check existing patterns** before creating new ones
3. **Document alongside development** using our standard format
4. **Place code in correct modules** following project structure
5. **Run tests** after each implementation step

## Key Principles

| **Principle** | **Description** |
|---------------|-----------------|
| **Test-First** | Write tests before implementing functionality |
| **Simplicity** | Prefer simple solutions over complex abstractions |
| **Documentation** | Document your changes alongside implementation |
| **Data Flow** | Follow the pipeline architecture and Parquet-first approach |