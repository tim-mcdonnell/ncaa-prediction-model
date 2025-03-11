# AI Task Example: Implement ESPN Game Parser

## Task Title: Implement ESPN Game Data Parser

> Develop a parser to transform raw ESPN API game response into our standardized format for storage.

## Context

The Collection Pipeline requires a parser component that can transform raw ESPN API responses (JSON) into a structured format suitable for our Parquet storage. This parser will handle the game data endpoint responses, extracting relevant fields and normalizing the data structure.

## Technical Background

- **Component**: Collection Pipeline - ESPN Parsers
- **Related Files**: 
  - `src/data/collection/espn/parsers.py` (to be implemented)
  - `src/data/collection/espn/models.py` (data models)
  - `tests/data/collection/espn/test_parsers.py` (to be implemented)
- **Dependencies**: 
  - Uses raw ESPN API response data
  - Outputs standardized data for the Parquet storage module

## Requirements

### Functional Requirements

- [ ] Parse basic game metadata (game_id, date, season, status)
- [ ] Extract team information (team_id, name, score)
- [ ] Parse venue information (venue_id, name, city, state)
- [ ] Handle different game statuses (scheduled, in-progress, final)
- [ ] Convert ESPN date formats to standard ISO format

### Technical Requirements

- [ ] Follow the Test-Driven Development approach by writing tests first
- [ ] Use type annotations for all functions and parameters
- [ ] Handle potential missing fields in the ESPN API response
- [ ] Implement error handling for malformed JSON data
- [ ] Document the function with docstring explaining parameters and return values

### Implementation Details

```python
# src/data/collection/espn/parsers.py

def clean_game_data(game_response: dict) -> dict:
    """
    Parse and transform ESPN API game response into standardized format.
    
    Args:
        game_response: Raw ESPN API response dictionary
        
    Returns:
        Standardized game data dictionary with consistent field names
        
    Raises:
        ValueError: If required fields are missing
    """
    # Expected implementation structure:
    # 1. Extract game metadata (id, date, season, status)
    # 2. Extract team information
    # 3. Extract venue information
    # 4. Transform to standardized format
    # 5. Validate required fields
    # 6. Return cleaned data
    pass
```

## Acceptance Criteria

- [ ] All tests pass (`uv python -m pytest tests/data/collection/espn/test_parsers.py -v`)
- [ ] Parser correctly handles all test fixtures in `tests/fixtures/espn_responses/`
- [ ] Function handles missing fields gracefully
- [ ] Implementation follows functional programming principles
- [ ] All dates are properly converted to ISO format (`YYYY-MM-DD`)

## Constraints

- Must handle all current ESPN API response formats without breaking changes
- Should be efficient with minimal memory overhead given large response payloads
- Parser should be pure function (no side effects, no external API calls)

## Resources

- [ESPN API Documentation](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b)
- [Sample ESPN response](tests/fixtures/espn_responses/sample_game.json)
- [ISO Date Format Specification](https://en.wikipedia.org/wiki/ISO_8601)

## Questions for Clarification

- How should we handle games with unknown venue information?
- Is there a specific format we want for team names (full name vs abbreviation)?
- Should we include conference information if available?

---

> **Note for AI Agent**: This task is crucial for the data collection pipeline. Focus on making the parser robust to various ESPN API response formats, as they might change slightly over time. 