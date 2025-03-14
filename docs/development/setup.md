# Development Environment Setup

This guide walks you through setting up your development environment for the NCAA Basketball Prediction Model.

## Prerequisites

- Python 3.11 or higher
- Git
- Basic familiarity with command line tools

## Step 1: Clone the Repository

```bash
git clone https://github.com/tim-mcdonnell/ncaa-prediction-model.git
cd ncaa-prediction-model
```

## Step 2: Set Up Python Environment

We use `uv` for dependency management. First, install `uv` if you don't have it already:

```bash
curl -sSf https://astral.sh/uv/install.sh | bash  # Unix/MacOS
# or
pip install uv  # Alternative
```

Next, create a virtual environment and install dependencies:

```bash
uv venv  # Creates a .venv directory
source .venv/bin/activate  # Unix/MacOS
# or
.venv\Scripts\activate  # Windows

# Install package and development dependencies
uv pip install -e ".[dev]"
```

## Step 3: Configure Git Hooks

We use pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

## Step 4: Run Tests to Verify Setup

```bash
pytest
```

If the tests pass, your development environment is set up correctly!

## IDE Configuration

### VS Code

We recommend the following VS Code extensions:

- Python (Microsoft)
- Pylance (Microsoft)
- Python Test Explorer
- Polars DataFrame Viewer

Suggested `settings.json` configuration:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### PyCharm

For PyCharm users, configure:

1. Set the project interpreter to your virtual environment
2. Enable Black formatter in Settings → Tools → Black
3. Configure Mypy in Settings → Tools → Mypy

## Development Workflow

After setting up your environment, we recommend:

1. Create a feature branch for your work: `git checkout -b feature/my-feature`
2. Follow the Test-Driven Development workflow as described in [testing.md](./testing.md)
3. Run tests frequently: `pytest`
4. Commit changes with descriptive messages
5. Create a pull request when your feature is ready

## Common Issues

### Dependency Conflicts

If you encounter dependency conflicts, try:

```bash
uv pip install --upgrade -e ".[dev]"
```

### Test Failures

If tests fail during setup:

1. Check Python version: `python --version` (should be 3.11+)
2. Verify dependencies are installed: `uv pip list`
3. Check for any error messages in test output

### Data Directory Setup

Some tests require a data directory structure. Create it with:

```bash
mkdir -p data/raw data/processed data/features
```

## Getting Help

If you need assistance with setup:

- Check the project documentation
- Open an issue on GitHub
- Contact the project maintainers 