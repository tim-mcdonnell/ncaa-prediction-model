# Test Strategy

## Philosophy and Approach

This project follows a strict Test-Driven Development (TDD) methodology, emphasizing the creation of tests before implementation. Our approach is built on these core principles:

1. **Tests First**: We write tests before implementing functionality to define expected behavior.
2. **Minimal Implementation**: We write only enough code to pass the current test.
3. **Continuous Refactoring**: We improve code design after tests pass without changing behavior.
4. **Progressive Development**: We implement solutions in logical stages rather than all at once.
5. **Strict Scope Management**: We implement only what is explicitly requested, minimizing feature creep.

## TDD Workflow

Every feature and component must follow this development cycle:

### 1. Requirement Analysis
- Break down requirements into testable behaviors
- Identify edge cases and boundary conditions
- Confirm scope understanding before beginning implementation

### 2. Red Phase
- Write a failing test that defines the expected behavior
- Name tests descriptively: `test[WhatIsTested]_[UnderWhatConditions]_[WithWhatExpectedResult]`
- Verify the test fails for the expected reason

### 3. Green Phase
- Write the simplest code possible to make the test pass
- Resist implementing functionality not covered by tests
- Run all tests to ensure no regressions

### 4. Refactor Phase
- Eliminate code smells and duplication
- Improve naming, structure, and organization
- Run tests after each refactoring step
- Document the code during this phase

## Test Categories

The test suite is organized into the following categories:

### Unit Tests

- Located in the primary test directories (`tests/data/`, `tests/features/`, etc.)
- Test individual components in isolation
- Mock dependencies as needed
- Should run quickly and reliably
- Focus on testing one specific behavior per test

Example:

```python
def test_point_differential_feature():
    # Create test data
    test_data = pl.DataFrame({
        "team_id": [1, 1, 2, 2],
        "season": [2022, 2022, 2022, 2022],
        "points": [75, 80, 65, 70],
        "points_allowed": [70, 75, 60, 65]
    })
    
    # Apply feature calculation
    calculator = PointDifferential()
    result = calculator.calculate(test_data)
    
    # Verify results
    assert result.shape[0] == 2  # Two teams
    assert result.filter(pl.col("team_id") == 1)["point_differential"][0] == 5.0
    assert result.filter(pl.col("team_id") == 2)["point_differential"][0] == 5.0
```

### Integration Tests

- Located in `tests/integration/`
- Test how components work together
- Minimal mocking, using realistic dependencies
- May involve slower processes like Parquet file operations
- Verify correct data flow between components

Example:

```python
def test_process_raw_games_pipeline():
    # Create sample raw data
    raw_df = pl.DataFrame({
        "game_id": ["123", "456"],
        "date": ["2022-01-01", "2022-01-02"],
        "home_team_id": ["team1", "team3"],
        "away_team_id": ["team2", "team4"],
        "home_score": [70, 65],
        "away_score": [65, 70],
        "neutral_site": [False, True]
    })
    
    # Apply transformation
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up temp directory structure
        raw_dir = Path(tmp_dir) / "raw" / "games" / "2022"
        raw_dir.mkdir(parents=True)
        
        # Save raw data
        raw_df.write_parquet(raw_dir / "games.parquet")
        
        # Override data path for testing
        with patch("src.data.storage.parquet_io.DATA_PATH", Path(tmp_dir)):
            # Process data
            result = process_raw_games(2022)
            
            # Verify processed data
            assert result.shape[0] == 2
            assert "home_win" in result.columns
            assert result.filter(pl.col("game_id") == "123")[0, "home_win"] == True
            assert result.filter(pl.col("game_id") == "456")[0, "home_win"] == False
            
            # Verify file was created
            processed_path = Path(tmp_dir) / "processed" / "games_unified.parquet"
            assert processed_path.exists()
```

### End-to-End Tests

- Located in `tests/integration/end_to_end/`
- Test complete workflows from data collection to model prediction
- Use small but realistic datasets
- May take longer to run
- Validate entire system behavior

## Testing Techniques

### Test Fixtures

Standard test fixtures are provided in `tests/fixtures/`:

- `espn_responses/`: Sample API responses for testing data collection
- `sample_data/`: Small datasets for feature engineering and model testing
- `expected_results/`: Expected outputs for verification

### Parameterized Testing

Use parameterized testing to evaluate components with multiple inputs:

```python
import pytest

@pytest.mark.parametrize("input_value,expected_output", [
    (1, 2),
    (2, 4),
    (3, 6)
])
def test_double_function(input_value, expected_output):
    assert double(input_value) == expected_output
```

### Mocking External Dependencies

Use the `unittest.mock` or `pytest-mock` libraries to isolate components from external dependencies:

```python
def test_espn_client(mocker):
    # Mock httpx client response
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"data": "sample"}
    mock_response.status_code = 200
    
    mocker.patch("httpx.AsyncClient.get", return_value=mock_response)
    
    # Test client with mocked httpx
    client = ESPNClient()
    result = await client.fetch_game("123456")
    assert result["data"] == "sample"
```

### Testing Data Flow

A key aspect of our architecture is testing data flow between components:

1. **Collection to Raw Storage**: Test ESPN client to raw Parquet flow
2. **Raw to Processed**: Test transformation of raw data to processed data
3. **Processed to Features**: Test feature engineering pipeline

Example:

```python
def test_game_collection_to_storage_flow():
    # 1. Set up mocked ESPN responses
    mock_espn_client = MockESPNClient()
    mock_espn_client.add_response(
        "schedule", 
        load_fixture("espn_responses/schedule_2022.json")
    )
    mock_espn_client.add_response(
        "game_123456", 
        load_fixture("espn_responses/game_123456.json")
    )
    
    # 2. Run collection pipeline with temporary storage
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Configure to use temporary directory
        collection_pipeline = CollectionPipeline(
            espn_client=mock_espn_client,
            data_dir=Path(tmp_dir)
        )
        
        # Run pipeline
        result = collection_pipeline.collect_games(
            season=2022, 
            game_ids=["123456"]
        )
        
        # 3. Verify raw data was stored correctly
        raw_parquet_path = Path(tmp_dir) / "raw" / "games" / "2022" / "games.parquet"
        assert raw_parquet_path.exists()
        
        # 4. Verify data content
        df = pl.read_parquet(raw_parquet_path)
        assert df.shape[0] == 1
        assert df[0, "game_id"] == "123456"
```

## Quality Assurance

### Test Coverage

- Aim for high test coverage (>90%) across the codebase
- Run coverage with `pytest --cov=src tests/`
- Generate reports with `pytest --cov=src --cov-report=html tests/`
- Focus on testing complex logic paths thoroughly

### Documentation Integration

- Use descriptive test names that serve as documentation
- Document public API methods during the refactor phase
- Tests themselves should demonstrate proper component usage

### Bug Handling Protocol

- When fixing bugs, first write a failing test that reproduces the bug
- When requirements change, modify or add tests first
- Never delete a test without a clear justification

## Development Process Integration

### CI/CD Integration

Tests are automatically run in the CI/CD pipeline:

- All tests must pass before merging to main
- Coverage reports are generated and tracked
- Unit tests run on every PR, integration tests run on merges to main

### Development Workflow

1. **Prioritize Test Development**: Focus on test creation before implementation
2. **Use Tests as Specifications**: Tests serve as living documentation of expected behavior
3. **Break Changes into Small Units**: Implement one test at a time to ensure focused progress
4. **Don't Skip Refactoring**: Take time to improve code after tests pass
5. **Review Test Coverage**: Regularly check for gaps in test coverage

### Balancing Efficiency with Control

For a productive development workflow:

1. **Autonomy Level**
   - For straightforward, low-risk tasks (simple methods, utility functions), implement complete solutions without interruption
   - For complex tasks, break implementation into logical chunks with review points
   - When uncertain about scope or requirements, pause and ask clarifying questions

2. **Decision Authority**
   - Make independent decisions on implementation details that don't affect architecture
   - Reserve key decision points for architectural choices and business logic interpretations
   - Get explicit confirmation before: git operations, adding dependencies, creating root folders, or deviating from architecture

## Test Organization Best Practices

1. Match test file structure to implementation structure
2. Name tests with clear descriptions of what they validate
3. Use setup/teardown methods for common test initialization
4. Keep tests independent and idempotent
5. Use appropriate assertions for different data types
6. Test functional pipelines by verifying inputs and outputs
7. Focus on testing behavior rather than implementation details
8. Prioritize readability and maintainability in test code