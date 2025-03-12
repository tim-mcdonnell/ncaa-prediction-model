# AI Implementation Task: Implement ESPN API Client

> **Note:** This document serves as the standard format for AI implementation tasks in this project. Use this example as a template when creating new AI tasks, adapting each section to the specific requirements while maintaining the overall structure.

## Overview
<!-- Single-sentence description of what the AI should implement -->
Create a robust, resilient ESPN API client for retrieving NCAA basketball data that handles rate limiting, error cases, and provides clean interfaces for the collection pipeline.

## Context
<!-- Brief explanation of why this component is needed and how it fits in the system -->
This client is the foundation of our data collection pipeline, responsible for reliably retrieving historical and current NCAA basketball game data from ESPN. All downstream data processing depends on this component's ability to fetch complete, accurate data while respecting API limitations.

## Technical Background
- **Pipeline Component**: Collection Pipeline - API Client
- **Related Files**: 
  - `src/utils/resilience/retry.py` <!-- Existing utility for retry logic -->
- **Key Endpoints**: 
  - `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` <!-- Example endpoint -->

## Requirements

### Functional Requirements
- Retrieve game data by season, including teams, scores, and game details
- Support configurable rate limiting to respect ESPN API constraints
- Implement retry mechanisms for transient failures
- Add logging for all API interactions
- Provide clear error messages with appropriate exception types

### Technical Requirements
- Use asynchronous HTTP requests with `aiohttp`
- Implement the context manager protocol for proper resource management
- Follow the project's resilience patterns for error handling
- Ensure all functions and classes have proper type annotations
- Keep resource usage efficient by managing connection pools properly

### Documentation Requirements
- Add comprehensive docstrings following the project's documentation standards
- Document public API methods with parameters, return types, and examples
- Create a usage guide showing common interaction patterns
- Include information about rate limiting and resilience features

### Test Requirements
- Create unit tests for all client functionality
- Implement test fixtures that mock ESPN API responses
- Test error handling and edge cases (network failures, malformed responses)
- Verify rate limiting and retry behavior

## Expected Interfaces

The client should support these general operations (exact implementation details are up to you):

```python
# General usage pattern (not prescriptive implementation)
async with ESPNClient(...) as client:
    # Get games for a specific season
    games_data = await client.get_games(season=2023)
    
    # Get specific game details
    game_details = await client.get_game_details(game_id="401524691")
```

## Project Guidelines
- **Test-Driven Development**: Write tests first before implementing functionality
- **Clean Architecture**: Separate concerns between HTTP handling, data validation, and business logic
- **Resilience First**: Assume the ESPN API will fail and design accordingly
- **Documentation Driven**: Document the public interface before implementing it
- **Consistency**: Follow patterns used in other parts of the codebase

## Integration Context
The ESPN client will be used by the Collection Pipeline to retrieve data, which will then transform and store it in Parquet format. The client doesn't need to know about downstream processing but should provide clean, consistently structured data.

## Practical Constraints
- ESPN API lacks official documentation, so the implementation requires flexibility
- ESPN may have undocumented rate limits - start conservatively and adjust based on testing
- The API will likely return inconsistent data structures across seasons - design for resilience

## Development Approach
1. **Write tests first** based on expected API behaviors and client interactions
2. Define interfaces with proper type annotations and comprehensive docstrings
3. Implement core functionality with minimal dependencies
4. Add resilience features (retries, rate limiting, etc.)
5. Document usage patterns and integration examples

---

> **Note for AI Agent**: Focus on designing a clean, resilient interface rather than specific implementation details. Start by writing tests that demonstrate how the client should behave, then implement to make those tests pass. This ensures the client meets the requirements without being constrained to a particular implementation approach. 