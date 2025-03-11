# Testing Strategy

## Test-Driven Development Approach

This project follows a strict Test-Driven Development (TDD) methodology. Every component should be developed following these steps:

1. **Write Tests First**: Before implementing any feature, write tests that define the expected behavior
2. **Run Tests (They Should Fail)**: Verify tests fail correctly before implementation
3. **Implement the Feature**: Write the minimum code necessary to pass the tests
4. **Run Tests Again**: Ensure the implementation passes all tests
5. **Refactor**: Clean up the implementation while ensuring tests still pass

## Test Categories

The test suite is organized into the following categories:

### Unit Tests

- Located in the primary test directories (`tests/data/`, `tests/features/`, etc.)
- Test individual components in isolation
- Mock dependencies as needed
- Should run quickly and reliably

### Integration Tests

- Located in `tests/integration/`
- Test how components work together
- Minimal mocking, using realistic dependencies
- May involve slower processes like Parquet file operations

### End-to-End Tests

- Located in `tests/integration/end_to_end/`
- Test complete workflows from data collection to model prediction
- Use small but realistic datasets
- May take longer to run

## Test Fixtures

Standard test fixtures are provided in `tests/fixtures/`:

- `espn_responses/`: Sample API responses for testing data collection
- `sample_data/`: Small datasets for feature engineering and model testing
- `expected_results/`: Expected outputs for verification

## Testing Data Flow

A key aspect of our revised architecture is testing data flow between components:

1. **Collection to Raw Storage**: Test ESPN client to raw Parquet flow
2. **Raw to Processed**: Test transformation of raw data to processed data
3. **Processed to Features**: Test feature engineering pipeline

Example of a data flow test:

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

## Parameterized Testing

Where appropriate, use parameterized testing to evaluate components with multiple inputs:

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

## Mocking External Dependencies

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

## Testing Data Processing

For testing data processing components (using Polars as per ADR-003):

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

## Testing Functional Pipelines

Our simplified architecture emphasizes functional pipelines. Test these by verifying transformations at each step:

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

## Test Coverage

Aim for high test coverage (>90%) across the codebase:

- Run coverage with `pytest --cov=src tests/`
- Generate reports with `pytest --cov=src --cov-report=html tests/`
- Focus on testing complex logic paths thoroughly

## CI/CD Integration

Tests are automatically run in the CI/CD pipeline:

- All tests must pass before merging to main
- Coverage reports are generated and tracked
- Unit tests run on every PR, integration tests run on merges to main

## Test Organization Best Practices

1. Match test file structure to implementation structure
2. Name tests with clear descriptions of what they validate
3. Use setup/teardown methods for common test initialization
4. Keep tests independent and idempotent
5. Use appropriate assertions for different data types
6. Test functional pipelines by verifying inputs and outputs
7. Focus on testing behavior rather than implementation details 