# AI Coding Agent Guide

This guide provides essential information for AI coding agents working on the NCAA Basketball Prediction Model.

## Quick Reference

| **Category** | **Key Points** |
|--------------|----------------|
| **Development Approach** | Test-Driven Development (TDD): Tests first, minimal implementation, then refactor with documentation in each phase |
| **Project Structure** | Pipeline architecture, Parquet storage, `src/` for code, `tests/` mirroring code structure |
| **Package Management** | ✅ Use `uv` for dependencies ❌ NEVER use pip directly |
| **Data Processing** | ✅ Use Polars for all data manipulation ❌ NEVER use pandas |
| **Terminal Commands** | ✅ Use `tmp/` files for multiline content ❌ NEVER use newlines in commands |

## Key Documentation

- **[Architecture Overview](../architecture.md)**: System design and components
- **[Test Strategy](./testing.md)**: Our TDD approach and testing practices
- **[Documentation Guide](./documentation.md)**: Documentation standards
- **[Development Workflow](./workflow.md)**: The complete development process
- **[Development Setup](./setup.md)**: Environment setup instructions

## TDD Workflow with Documentation

Documentation is an essential part of the TDD cycle, not an afterthought:

1. **Red Phase:**
   - Write failing tests first
   - Document expected behavior in test docstrings
   - Define the interface and expected outcomes
   
2. **Green Phase:**
   - Write minimal code to pass tests
   - Include proper docstrings as you implement
   - Focus on clear parameter and return type documentation
   
3. **Refactor Phase:**
   - Improve code without changing behavior
   - Enhance docstrings with examples and notes
   - Update component documentation if necessary

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

For detailed component information, see the [architecture documentation](../architecture.md) and specific component docs in the `docs/components/` directory.

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

## Adding New Features

The feature pipeline is a central part of our system. When adding new features:

1. Start with a test that defines the expected behavior
2. Implement the feature calculator class
3. Register the feature in the feature registry
4. Document the feature in code and component documentation

For detailed instructions, see [Adding Features Guide](../guides/adding_features.md).

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

## File Organization

Our documentation is organized into these main sections:

- **Top-level**: Project overview and architecture (`docs/index.md`, `docs/architecture.md`)
- **Development**: Guides for developers (`docs/development/`)
- **Components**: Documentation for major system components (`docs/components/`)
- **Guides**: Task-oriented how-to guides (`docs/guides/`)
- **Reference**: Auto-generated API docs (`docs/reference/`)

When implementing features, be sure to check the appropriate component documentation and update it if necessary.

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
    description = "Points scored per 100 possessions"
    dependencies = ["team_possessions"]
    required_data = ["games", "teams"]
    
    def calculate(self, data: dict[str, pl.DataFrame]) -> pl.DataFrame:
        # Implementation using Polars
```

## Documentation in the TDD Cycle

For each TDD cycle, include documentation as follows:

1. **Test Documentation (Red Phase)**
   ```python
   def test_function_behavior():
       """
       Test that the function does X when given Y and returns Z.
       
       This test verifies:
       - Specific behavior A
       - Edge case B
       - Error handling C
       """
   ```

2. **Implementation Documentation (Green Phase)**
   ```python
   def function_name(param1: Type1, param2: Type2) -> ReturnType:
       """
       Brief description of function purpose.
       
       Args:
           param1: Description of param1
           param2: Description of param2
           
       Returns:
           Description of return value
       """
   ```

3. **Refactor Documentation (Refactor Phase)**
   - Enhance docstrings with examples
   - Add notes about implementation details
   - Update component documentation if necessary

## Key Principles

| **Principle** | **Description** |
|---------------|-----------------|
| **Test-First** | Write tests before implementing functionality |
| **Documentation Alongside** | Document your changes during development, not after |
| **Simplicity** | Prefer simple solutions over complex abstractions |
| **Data Flow** | Follow the pipeline architecture and Parquet-first approach |