# ESPN API Response Fixtures

This directory contains standardized fixtures for ESPN API responses used in testing the ESPN client and related components.

## Available Fixtures

- **scoreboard_response.json**: Example response from the scoreboard endpoint with data for a completed game
- **game_summary_response.json**: Example response from the game summary endpoint with boxscore and play-by-play data
- **teams_response.json**: Example response from the teams list endpoint showing multiple teams
- **team_response.json**: Example response from the team endpoint with detailed information about a specific team

## Usage

These fixtures are used in unit tests for the ESPN client, parsers, and integration tests. You can load them in tests using the `fixture_path` and `load_fixture` fixtures defined in `tests/data/collection/espn/conftest.py`:

```python
def test_example(load_fixture):
    # Load a fixture from the standard location
    data = load_fixture("scoreboard_response.json")
    # Use the fixture data in tests
    ...
```

## Maintenance

When updating these fixtures:

1. Ensure they contain realistic but anonymized data
2. Make sure they include all required fields for validation
3. Document any modifications in this README
4. Consider the impact on existing tests that depend on these fixtures

## Structure

All fixtures follow the actual ESPN API response format and include a representative subset of data sufficient for testing all client functionality. 