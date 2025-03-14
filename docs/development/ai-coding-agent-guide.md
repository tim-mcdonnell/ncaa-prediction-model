# AI Coding Agent Guide

This guide provides essential information for AI coding agents working on the NCAA Basketball Prediction Model.

## Quick Reference

| **Category** | **Key Points** |
|--------------|----------------|
| **Development Approach** | Test-Driven Development (TDD): Tests first, minimal implementation, then refactor |
| **Package Management** | ✅ Use `uv` for dependencies ❌ NEVER use pip directly |
| **Data Processing** | ✅ Use Polars for all data manipulation ❌ NEVER use pandas |
| **Terminal Commands** | ✅ Use `tmp/` files for multiline content ❌ NEVER use newlines in commands |
| **Testing** | ✅ Use `python -m pytest` ❌ NEVER use bare `pytest` command |
| **GitHub Issues** | ✅ Use `gh issue view #` ❌ NEVER search directories for issues |

## Key Documentation

- **[Test Strategy](./development/testing.md)**: Our TDD approach and testing practices
- **[Documentation Guide](./development/documentation.md)**: Documentation standards
- **[Architecture Overview](./architecture.md)**: System design and components

## ⚠️ Critical Workflow Issues ⚠️

### 1. GitHub Issue Access

ALWAYS use GitHub CLI to view issues, not file searches:

```bash
# ✅ CORRECT: View issue details directly
gh issue view 11
```

### 2. Running Tests

ALWAYS use the module format to run pytest:

```bash
# ✅ CORRECT: Run tests with proper Python path resolution
python -m pytest tests/pipelines/test_base_pipeline.py
```

## Project Structure Guidelines

```
ncaa-prediction-model/
├── src/                  # Production code ONLY
├── tests/                # Tests (mirroring src structure)
├── examples/             # CODE EXAMPLES (executable Python)
└── docs/
    └── development/
        └── examples/     # DEVELOPMENT EXAMPLES (PR/issue templates)
```

### Three Types of Examples:

1. **Code Examples** - Go in `/examples` (project root)
   - Executable Python code demonstrating library usage
   
2. **Development Examples** - Go in `/docs/development/examples`
   - Templates for project management (PRs, issues, tasks)
   - Do NOT modify unless instructed
   
3. **Documentation Examples** - Go in `/docs/examples` (if needed)
   - Only create if specifically instructed

❌ NEVER create code examples in `src/` or `docs/` directories

## TDD Workflow

1. **Red Phase:** Write failing tests first
2. **Green Phase:** Write minimal code to pass tests
3. **Refactor Phase:** Improve code without changing behavior

## Architecture Overview

```
Collection Pipeline → Processing Pipeline → Feature Pipeline → Prediction Pipeline
                                                      ↓
                                            Daily Update Pipeline
```

All pipeline components are in `src/pipelines/` - examples go in root `/examples/` directory.

## Common Mistakes to Avoid

### GitHub Workflow

```bash
# ✅ CORRECT: Use GitHub CLI for all issue operations
run_terminal_cmd("gh issue view 11")
```

### Test Execution

```bash
# ✅ CORRECT: Always use module format for pytest
run_terminal_cmd("python -m pytest tests/path/to/test_file.py")

# ❌ INCORRECT: Don't run pytest directly
# run_terminal_cmd("pytest tests/path/to/test_file.py")
```

### Data Processing

```python
# ✅ CORRECT
import polars as pl
df = pl.read_parquet("path/to/file.parquet")

# ❌ INCORRECT
# import pandas as pd
```

## ⚠️ Terminal Command Limitations ⚠️

Terminal commands with newlines WILL FAIL. Always use temporary files:

```python
# 1. Create temporary file
edit_file("tmp/commit_msg.md", """Feature: Add functionality

- Add component
- Implement feature""")

# 2. Use in command
run_terminal_cmd("git commit -F tmp/commit_msg.md")

# 3. Clean up
delete_file("tmp/commit_msg.md")
```

## Checkpoint Requirements

Always get explicit confirmation before:
- Git operations (commits, pushes, branch creation)
- Adding new dependencies
- Creating new root folders
- Deviating from project architecture

## Key Principles

| **Principle** | **Description** |
|---------------|-----------------|
| **Test-First** | Write tests before implementing functionality |
| **Simplicity** | Prefer simple solutions over complex abstractions |
| **Documentation** | Document your changes alongside implementation |