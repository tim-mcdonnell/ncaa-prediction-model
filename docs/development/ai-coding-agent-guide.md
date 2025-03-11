# AI Coding Agent Guide

This guide is designed for AI coding agents working on the NCAA Basketball Prediction Model. It provides a high-level overview of the project architecture, development practices, and common pitfalls to avoid.

## Quick Reference

| **Category** | **Key Points** |
|--------------|----------------|
| **Project Structure** | Pipeline-based architecture, Parquet-first storage |
| **Development Approach** | Test-Driven Development, Progressive Abstraction |
| **Package Management** | Use `uv` (not pip) for dependency management |
| **Data Processing** | Use Polars (not pandas) for all data manipulation |
| **Storage** | Direct Parquet files (no SQL database) |

## Project Documentation

Start by familiarizing yourself with these key documents:

- **[Project Structure](./project-structure.md)**: Overview of directory organization
- **[Pipeline Architecture](./pipeline-architecture.md)**: Core data flow design
- **[Modularity Guidelines](./modularity-guidelines.md)**: Code organization principles
- **[Test Strategy](./test-strategy.md)**: Testing approach and practices

For implementation, refer to:

- **[Implementation Plan](./implementation-plan.md)**: Phase-by-phase development roadmap

## Architecture Overview

This project uses a **pipeline architecture** with these key components:

```
Collection Pipeline → Processing Pipeline → Feature Pipeline → Prediction Pipeline
                                                      ↓
                                            Daily Update Pipeline
```

1. **Collection Pipeline**: Fetches data from ESPN APIs
2. **Processing Pipeline**: Transforms raw data into standardized formats
3. **Feature Pipeline**: Calculates 60+ basketball metrics with dependency resolution
4. **Prediction Pipeline**: Generates predictions using the latest features and trained models
5. **Daily Update Pipeline**: Combines all pipelines for efficient daily updates during basketball season

**Key Implementation Files**:
- `/src/pipelines/base_pipeline.py`: Base class with shared functionality
- `/src/pipelines/collection_pipeline.py`: Data collection orchestration
- `/src/pipelines/processing_pipeline.py`: Data transformation orchestration
- `/src/pipelines/feature_pipeline.py`: Feature calculation orchestration
- `/src/pipelines/prediction_pipeline.py`: Prediction orchestration
- `/src/pipelines/daily_update.py`: Combined daily update pipeline

## Development Practices

### Test-Driven Development

- **Write tests first**: Create tests before implementing functionality
- **Test fixtures**: Use fixtures in `/tests/fixtures/` for consistent test data
- **Test structure**: Match test directory structure to source code

### Progressive Abstraction

- Start with concrete implementations and refactor to abstractions as patterns emerge
- Focus on functionality first, then optimize for reusability
- Document design decisions when introducing abstractions

## Common Mistakes to Avoid

### Package Management

❌ **NEVER use pip directly**  
✅ **ALWAYS use uv**: `uv pip install -e .`

Package management commands:
```bash
# Install dependencies
uv pip install -e .

# Add a new dependency (updates pyproject.toml automatically)
uv pip install package_name
```

### Terminal Command Limitations

❌ **NEVER include newline characters in terminal commands**  
✅ **ALWAYS use a separate file for multiline content**

Terminal commands with newlines will fail. This is particularly important for:
- Git commit messages
- GitHub issue creation
- Complex commands with multiple lines

Examples of correct approaches:

```bash
# INCORRECT - Will fail due to newlines
git commit -m "Add feature X

This implements the new feature with:
- Component A
- Component B"

# CORRECT - Use a temp file for multiline content
cat > commit_msg.txt << 'EOF'
Add feature X

This implements the new feature with:
- Component A
- Component B
EOF
git commit -F commit_msg.txt

# CORRECT - For GitHub issues, use the -F flag
gh issue create -t "Issue Title" -F issue_description.md
```

### Data Processing

❌ **NEVER use pandas for data processing**  
✅ **ALWAYS use Polars**: 

```python
# Correct approach
import polars as pl

df = pl.read_parquet("path/to/file.parquet")
result = df.filter(pl.col("column") > 0).groupby("category").agg(pl.sum("value"))
```

### Data Storage

❌ **NEVER create database abstractions or custom ORMs**  
✅ **ALWAYS use Parquet files directly**:

```python
# Correct approach - use the storage utilities
from src.data.storage.parquet_io import save_parquet, load_parquet

# Loading data
df = load_parquet(data_category="raw", filename="games/2023/games")

# Saving data
save_parquet(df, data_category="processed", filename="games_unified")
```

### Code Organization

❌ **NEVER add code to the wrong module**  
✅ **ALWAYS follow the project structure**:

- Data collection code goes in `src/data/collection/`
- Feature calculations go in `src/features/`
- Pipeline orchestration goes in `src/pipelines/`

### Error Handling

❌ **NEVER use naked try/except blocks**  
✅ **ALWAYS handle specific exceptions and use the resilience patterns**:

```python
# Correct approach
from src.utils.resilience.retry import retry

@retry(max_attempts=3, backoff_factor=1.5)
async def fetch_data(url):
    # Implementation
```

## Pipeline Implementation Guidelines

### 1. Collection Pipeline

- Use the ESPN client in `src/data/collection/espn/client.py`
- Follow the incremental update pattern for efficient daily updates
- Store raw data in Parquet files in the `data/raw/` directory

### 2. Feature Pipeline

- Implement features as classes that inherit from `src.features.base.Feature`
- Specify dependencies and required data for automatic resolution
- Use pure functions for data transformations
- Register features in the feature registry

Example feature implementation:
```python
from src.features.base import Feature
import polars as pl

class OffensiveEfficiencyFeature(Feature):
    id = "team_offensive_efficiency"
    name = "Team Offensive Efficiency"
    dependencies = ["team_possessions"]
    required_data = ["games", "teams"]
    
    def calculate(self, data: dict[str, pl.DataFrame]) -> pl.DataFrame:
        # Implementation using Polars
```

## Code Contribution Tips

1. **Check existing implementations** before creating new patterns
2. **Reference the pipeline architecture documentation** for flow design
3. **Use functional patterns** for data transformations
4. **Write tests for all code** following the test strategy
5. **Document non-obvious design decisions** in comments

## Need Help?

If you encounter anything not covered in this guide:

1. **Start with the project documentation** in the `/docs/` directory
2. **Refer to the code structure** to understand existing patterns
3. **Check test implementations** for usage examples
4. **Ask for clarification** before implementing significant changes

## Remember

- The project prioritizes **simplicity** and **clarity** over complex abstractions
- **Test everything** thoroughly through both unit and integration tests
- **Document your changes** to help future developers (including other AI agents)
- **Follow the Parquet-first approach** and pipeline architecture for all implementations 