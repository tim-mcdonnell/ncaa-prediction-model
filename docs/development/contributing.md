# Contributing Guide

Thank you for your interest in contributing to the NCAA Basketball Prediction Model! This document outlines the process for contributing to the project.

## Getting Started

### 1. Set Up Your Environment

Follow the steps in the [Development Setup](setup.md) guide to set up your local development environment.

### 2. Find an Issue

- Browse the [GitHub Issues](https://github.com/yourusername/ncaa-prediction-model/issues) for the project
- Look for issues labeled `good first issue` if you're new to the project
- Check the [Milestones](../milestones/index.md) documentation to understand the project roadmap

### 3. Create a Branch

Create a new branch for your contribution:

```bash
git checkout -b feature/your-feature-name
```

Use prefixes in your branch name to indicate the type of change:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation changes
- `refactor/` for code refactoring

## Development Workflow

### Coding Standards

Follow the project's [Code Standards](code-standards.md) for consistent style and quality.

### Commit Guidelines

Write clear, concise commit messages that explain what changes were made and why:

```
<type>: <summary>

<body>
```

Where `<type>` is one of:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Routine tasks, dependency updates, etc.

Example:
```
feat: Add team strength calculation to feature engineering

Implements the Elo rating system for calculating team strength based on
historical game results. Addresses milestone #3, task #42.
```

### Testing

- Write tests for all new features and bug fixes
- Ensure all tests pass before submitting a PR
- Run tests using pytest:
  ```bash
  pytest
  ```

### Documentation

- Update documentation for any feature or API changes
- Document new functions, classes, and modules with docstrings
- Preview documentation changes locally using `mkdocs serve`

## Pull Request Process

### 1. Keep PRs Focused

Each pull request should address a single concern. If you're working on multiple features, create separate branches and PRs.

### 2. Submit Your PR

- Push your branch to GitHub
- Create a pull request against the `main` branch
- Use the PR template to provide details about your changes

### 3. Code Review

- All PRs require review from at least one maintainer
- Address any feedback from code reviews
- Make requested changes and push to the same branch

### 4. PR Approval and Merge

- PRs will be merged once they've been approved
- PRs should pass all CI checks before merging
- Maintainers will merge approved PRs

## Milestone Contributions

When working on milestones:

1. Review the milestone documentation in detail
2. Discuss your approach on the associated issue before starting work
3. Break down your contribution into manageable PRs
4. Update the milestone documentation with progress

## Getting Help

If you need help with anything:

- Ask questions on the issue you're working on
- Reach out to the maintainers
- Check the documentation for guidance

Thank you for contributing! 