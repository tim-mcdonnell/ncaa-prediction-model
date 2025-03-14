# Generating API Documentation

This guide explains how to generate and maintain API reference documentation for the NCAA Basketball Prediction Model.

## Overview

API documentation is automatically generated from docstrings in the source code. This ensures that the documentation stays in sync with the codebase and reduces manual effort. We use [mkdocstrings](https://mkdocstrings.github.io/) with our custom generation script to produce comprehensive API reference pages.

## Writing Docstrings

For documentation to be generated correctly, follow these guidelines for writing docstrings:

### Google-Style Docstrings

Use Google-style docstrings for all public functions, classes, and methods:

```python
def calculate_offensive_efficiency(team_data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate offensive efficiency (points per 100 possessions) for each team.
    
    Args:
        team_data: DataFrame with columns [team_id, points, possessions]
            
    Returns:
        DataFrame with columns [team_id, offensive_efficiency]
        
    Raises:
        ValueError: If required columns are missing
        
    Example:
        ```python
        # Calculate efficiency
        efficiency = calculate_offensive_efficiency(team_stats)
        ```
    """
```

### Module-Level Docstrings

Include a module-level docstring in each Python file:

```python
"""
Team performance metrics calculation module.

This module provides functions and classes for calculating 
various basketball analytics metrics at the team level.
"""
```

## Generating Documentation

API documentation is automatically generated when the documentation site is built. To manually generate the API documentation:

```bash
# Run from the project root
cd docs
python gen_ref_pages.py
```

This will:
1. Scan all Python files in the `src/` directory
2. Create Markdown files in `docs/reference/` with API documentation
3. Build a navigation structure for the documentation

## Viewing Generated Documentation

After generating documentation, you can preview it using:

```bash
# Run from the project root
mkdocs serve
```

Then visit http://127.0.0.1:8000 in your browser and navigate to the Reference section.

## Customizing Documentation Generation

The documentation generation script (`gen_ref_pages.py`) can be customized if needed:

```python
# Exclude certain modules
if "experimental" in module_dots:
    continue

# Add custom content to generated files
fd.write("## Custom Section\n\n")
fd.write("Additional information about this module.\n\n")
```

## Troubleshooting

### Missing Documentation

If documentation for a module or function isn't appearing:

1. Check that the docstring follows the Google-style format
2. Ensure the module isn't being skipped (e.g., `__init__.py` with only imports)
3. Verify that the module is importable (no syntax errors)

### Documentation Errors

If you see errors in the generated documentation:

1. Check for syntax errors in your docstrings
2. Ensure code examples in docstrings are properly indented
3. Verify that type hints are correctly formatted

## Integration with TDD Workflow

Documentation generation fits into our TDD workflow as follows:

1. **Red Phase**: Write test with docstring explaining what's being tested
2. **Green Phase**: Implement with basic docstrings
3. **Refactor Phase**: Enhance docstrings with examples and notes
4. **Documentation**: Run `gen_ref_pages.py` to generate API docs

Remember that comprehensive docstrings serve as both documentation and usage examples for developers using your code. 