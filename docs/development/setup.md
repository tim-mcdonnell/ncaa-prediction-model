# Development Setup

This guide will help you set up your development environment for the NCAA Basketball Prediction Model project.

## Prerequisites

- Python 3.11 or higher
- Git
- [uv](https://github.com/astral-sh/uv) package manager

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ncaa-prediction-model.git
cd ncaa-prediction-model
```

### 2. Create a Virtual Environment

We use `uv` to manage our virtual environments and dependencies:

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install the project in development mode with all dependencies
uv pip install -e ".[dev]"
```

## Running the Documentation Locally

To preview the documentation site locally:

```bash
# Start the MkDocs development server
mkdocs serve
```

This will start a local server at http://127.0.0.1:8000/ where you can preview the documentation.

## Code Quality Tools

### Ruff for Linting and Formatting

We use Ruff for linting and code formatting:

```bash
# Run linting
ruff check .

# Run formatting
ruff format .
```

### MyPy for Type Checking

```bash
# Run type checking
mypy .
```

### Pytest for Testing

```bash
# Run tests
pytest
```

## Working with Milestones

When working on a specific milestone:

1. Check the milestone details in `docs/milestones/`
2. Break down the milestone into specific tasks
3. Create branches for each feature or task 
4. Submit pull requests when features are complete

## Documentation

Always update documentation alongside code changes:

1. Document new modules with proper docstrings
2. Update relevant markdown files in the `docs/` directory
3. Preview changes with `mkdocs serve` 