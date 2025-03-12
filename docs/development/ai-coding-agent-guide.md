# AI Coding Agent Guide

This guide provides essential information for AI coding agents working on the NCAA Basketball Prediction Model. It covers project architecture, development practices, and common pitfalls to avoid.

## Quick Reference

| **Category** | **Key Points** |
|--------------|----------------|
| **Project Structure** | Pipeline-based architecture, Parquet-first storage |
| **Development Approach** | Test-Driven Development, Progressive Abstraction |
| **Package Management** | Use `uv` (not pip) for dependency management |
| **Data Processing** | Use Polars (not pandas) for all data manipulation |
| **Storage** | Direct Parquet files (no SQL database) |
| **GitHub Management** | Use GitHub API for milestones, store multiline content in `/tmp` |
| **Terminal Commands** | Avoid newlines, use `/tmp` for multiline content |

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

## ⚠️ Critical Terminal Command Limitations ⚠️

One of the most common issues AI agents encounter is with terminal commands containing newlines.

### The Problem:

❌ **Terminal commands with newline characters WILL FAIL** ❌

```bash
# THIS WILL FAIL - Do not attempt this approach
git commit -m "First line of commit message
Second line of commit message"
```

### The Solution:

✅ **ALWAYS use a temporary file in `/tmp` for any multiline content** ✅

Follow this exact pattern for all multiline content:

```bash
# 1. Create a temporary file with your content
echo "Title of commit/PR/issue" > /tmp/message.txt
echo "" >> /tmp/message.txt  # Add blank line
echo "Detailed description goes here." >> /tmp/message.txt

# 2. Use the file in your command
git commit -F /tmp/message.txt
# OR
gh pr create --title "Title" --body-file /tmp/message.txt
# OR
gh issue create --title "Title" --body-file /tmp/message.txt

# 3. Clean up (optional)
rm /tmp/message.txt
```

This pattern is REQUIRED for:
- Git commit messages
- GitHub PR descriptions
- GitHub issue creation
- GitHub milestone descriptions
- Any command with multiple lines

### GitHub Project Management

Use GitHub CLI to work with issues, milestones, and other project components:

#### Accessing Issues

```bash
# View issue #1
gh issue view 1

# View issue #1 with all comments
gh issue view 1 --comments

# View issue #1 in web browser
gh issue view 1 --web
```

#### Managing Milestones

GitHub CLI doesn't have direct milestone commands, so use the GitHub API:

```bash
# Get milestone details
gh api /repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/milestones/1 \
  -q '.title, .description, .open_issues, .closed_issues'

# List all issues in a milestone
gh issue list --milestone 1 --state all

# Create a milestone (using /tmp for multiline content)
cat > /tmp/milestone_description.txt << 'EOF'
Milestone description with multiple lines
EOF

gh api --method POST /repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/milestones \
  -f title="New Milestone" \
  -f description="$(cat /tmp/milestone_description.txt)" \
  -f state="open" \
  -q '.number'

rm /tmp/milestone_description.txt

# Edit a milestone
cat > /tmp/updated_description.txt << 'EOF'
Updated description
EOF

gh api --method PATCH /repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/milestones/1 \
  -f title="Updated Title" \
  -f description="$(cat /tmp/updated_description.txt)" \
  -f state="open"

rm /tmp/updated_description.txt
```

#### Creating and Updating Issues

```bash
# Create an issue with milestone assignment
cat > /tmp/issue.md << 'EOF'
Detailed description with requirements
EOF

gh issue create --title "Issue Title" --body-file /tmp/issue.md --milestone "1"
rm /tmp/issue.md

# Add existing issue to milestone
gh api --method PATCH /repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues/5 \
  -f milestone=1
```

When implementing a task, always review the complete task description to understand:
- Requirements and acceptance criteria
- Context and background information
- Related tasks and dependencies
- Implementation guidance

The task descriptions follow the format in `docs/development/examples/ai_task_example.md`.

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

| **Pipeline** | **Key Guidelines** |
|--------------|-------------------|
| **Collection** | • Use ESPN client in `src/data/collection/espn/client.py`<br>• Follow incremental update pattern<br>• Store raw data in `data/raw/` directory |
| **Feature** | • Inherit from `src.features.base.Feature`<br>• Specify dependencies and required data<br>• Use pure functions for transformations<br>• Register in feature registry |

Example feature:
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

## Key Principles

| **Principle** | **Description** |
|---------------|-----------------|
| **Simplicity** | Prefer simple solutions over complex abstractions |
| **Testability** | Write comprehensive tests for all functionality |
| **Documentation** | Document your changes and reasoning |
| **Data Flow** | Follow the pipeline architecture and Parquet-first approach |
| **Compatibility** | Ensure new code integrates with existing components |
| **Organization** | Place code in the appropriate modules following project structure | 