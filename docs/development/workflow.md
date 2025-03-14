# Development Workflow

This guide outlines the recommended workflow for developing features and fixes for the NCAA Basketball Prediction Model.

## Overview

We follow a Test-Driven Development (TDD) workflow with these core principles:

1. Write tests first to define expected behavior
2. Implement minimal code to make tests pass
3. Refactor while keeping tests passing
4. Document as you go, not as an afterthought

## Development Cycle

### 1. Prepare

1. **Pull the latest changes**:
   ```bash
   git checkout main
   git pull
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/descriptive-name
   ```

3. **Plan your approach**:
   - Identify the component you'll be modifying
   - Review existing tests and documentation
   - Break down the work into small, testable increments

### 2. Test-Driven Development Cycle

#### Red Phase: Write a Failing Test

1. Create or modify a test file:
   ```bash
   # Example for adding a new feature
   touch tests/features/test_new_feature.py
   ```

2. Write a test that defines expected behavior:
   ```python
   def test_feature_calculation():
       """Test that the feature calculates expected values."""
       # Test setup and assertions...
   ```

3. Run the test to verify it fails:
   ```bash
   pytest tests/features/test_new_feature.py -v
   ```

#### Green Phase: Make the Test Pass

1. Implement the minimal code needed to pass the test:
   ```bash
   # Example for adding a new feature
   touch src/features/new_feature.py
   ```

2. Write the implementation:
   ```python
   class NewFeature(Feature):
       """Feature implementation..."""
       # Minimal implementation to pass the test
   ```

3. Run the test to verify it passes:
   ```bash
   pytest tests/features/test_new_feature.py -v
   ```

#### Refactor Phase: Improve the Code

1. Refactor your code to improve design without changing behavior
2. Run tests after each refactoring step to ensure they still pass
3. Consider:
   - Code structure
   - Naming
   - Performance
   - Documentation

### 3. Document

Documentation should be written alongside your code, not as a separate step:

1. **Code Documentation**:
   - Write clear docstrings in Google format
   - Add comments for complex logic
   - Update type hints

2. **Component Documentation**:
   - Update relevant documentation in `docs/components/`
   - Add examples if appropriate

3. **Guide Documentation**:
   - If adding a significant feature, update or create guides in `docs/guides/`

### 4. Review and Submit

1. **Run the full test suite**:
   ```bash
   pytest
   ```

2. **Run linting and type checking**:
   ```bash
   pre-commit run --all-files
   ```

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Feature: Add descriptive message"
   ```

4. **Push and create a pull request**:
   ```bash
   git push -u origin feature/descriptive-name
   ```

5. Respond to review comments and make necessary changes

## Example Workflow

Here's an example workflow for adding a new feature:

```bash
# Start with a fresh branch
git checkout main
git pull
git checkout -b feature/add-turnover-rate

# Create test file
# Edit tests/features/test_turnover_rate.py with test cases

# Run the test (it should fail)
pytest tests/features/test_turnover_rate.py -v

# Implement the feature
# Edit src/features/turnover.py with implementation

# Run the test (it should pass)
pytest tests/features/test_turnover_rate.py -v

# Refactor if needed
# Update the implementation while keeping tests passing

# Update documentation
# Edit docs/components/features.md to mention the new feature

# Run all tests and checks
pytest
pre-commit run --all-files

# Commit and push
git add .
git commit -m "Feature: Add turnover rate calculation"
git push -u origin feature/add-turnover-rate

# Create pull request on GitHub
```

## Best Practices

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Use descriptive variable names
- Keep functions small and focused
- Use docstrings for all public functions and classes

### Test Standards

- Test both normal cases and edge cases
- Use meaningful test names that describe what is being tested
- Keep tests isolated from each other
- Write clear assertion messages
- Don't test private implementation details

### Git Standards

- Use descriptive branch names (feature/, fix/, refactor/)
- Keep commits focused on single logical changes
- Write clear commit messages
- Rebase branch before submitting PR
- Merge only after CI passes and approval

## Troubleshooting

### Failing Tests

If tests are failing:

1. Read the error message carefully
2. Check the test expectations against your implementation
3. Add print statements or use a debugger to trace execution
4. Verify input data and expected outputs

### Merge Conflicts

If you encounter merge conflicts:

1. Pull the latest changes from main
2. Resolve conflicts locally
3. Run tests after resolving conflicts
4. Commit the resolved conflicts

```bash
git checkout main
git pull
git checkout your-branch
git merge main
# Resolve conflicts
git add .
git commit -m "Merge main and resolve conflicts"
``` 