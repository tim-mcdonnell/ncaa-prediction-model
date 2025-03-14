# NCAA Prediction Model Examples

This directory contains executable examples demonstrating how to use various components of the NCAA Prediction Model.

## Available Examples

### Pipeline Examples

- **[Simple Pipeline Example](./pipelines/simple_pipeline_example.py)**: Demonstrates the use of the base pipeline framework with a simple transformation pipeline.

## Running Examples

To run an example:

```bash
# Run from the project root directory
python -m examples.pipelines.simple_pipeline_example
```

## Creating New Examples

When adding new examples:

1. Place them in the appropriate subdirectory based on component type
2. Use clear, descriptive names ending with `_example.py`
3. Include a `run_example()` function and make the file executable
4. Add proper documentation with docstrings
5. Add the example to this README

## Directory Structure

```
examples/
├── README.md                        # This file
├── pipelines/                       # Pipeline examples
│   └── simple_pipeline_example.py   # Simple pipeline example
└── features/                        # Feature calculation examples (future)
```

## Example Code Standards

- Examples should be well-documented with comments
- Include realistic but simple test data
- Show both basic and advanced usage patterns
- Handle errors gracefully
- Include proper cleanup of resources 