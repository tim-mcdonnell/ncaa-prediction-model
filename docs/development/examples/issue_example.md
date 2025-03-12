# ESPN API Authentication Issue

> **Note:** This document serves as the standard format for GitHub issues in this project. Use this example as a template when creating new issues, adapting each section to the specific issue while maintaining the overall structure.

## Issue Type
- [x] Bug: Something isn't working as expected
- [ ] Feature Request: New functionality needed
- [ ] Performance: Optimization or efficiency issue
- [ ] Documentation: Documentation missing or incorrect
- [ ] Technical Debt: Refactoring or code quality issue

## Priority
- [ ] Critical: Blocking development or production issue
- [x] High: Important but not blocking 
- [ ] Medium: Should be addressed soon
- [ ] Low: Nice to have

## Quick Summary
ESPN API integration fails with authentication errors despite using the documented public endpoints. API client returns 401 Unauthorized errors when attempting to fetch season data.

## Details

### Current Behavior
The ESPN API client returns 401 Unauthorized errors when making requests to the `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` endpoint, despite this being a publicly documented endpoint that should not require authentication.

### Expected Behavior
API client should successfully retrieve data from ESPN endpoints without authentication errors, as these are supposed to be public-facing APIs.

### Reproduction Steps
1. Initialize the ESPNClient with the base URL `https://site.api.espn.com/apis/site/v2/`
2. Call the `get_games(season=2023)` method
3. Observe the 401 Unauthorized error response

### Context & Environment
- Python 3.11.4
- aiohttp 3.8.5
- Running locally on macOS 14.0
- Error occurs consistently across multiple attempts and with different ESPN endpoints

### Screenshots/Logs
```
ERROR:espn_client:API request failed: 401 Unauthorized
Traceback (most recent call last):
  File "src/data/collection/espn/client.py", line 87, in get_resource
    response.raise_for_status()
  File "aiohttp/client_reqrep.py", line 1021, in raise_for_status
    raise ClientResponseError(...)
aiohttp.client_exceptions.ClientResponseError: 401, message='Unauthorized'
```

## Milestone & Related Issues
- **Related Milestone:** #1 Data Collection and Storage
- **Related Issues:** #3 Implement ESPN API Client

## Proposed Solution
Investigate adding required headers to API requests:
1. Add a proper User-Agent header to mimic a browser request
2. Explore potential hidden authentication requirements in ESPN API
3. Consider using browser-like request patterns with appropriate referrer headers

---

<!-- For core team use, do not fill out when creating an issue -->
## Resolution Plan
- [ ] Add browser-like User-Agent header to all requests
- [ ] Implement referrer header with espn.com domain
- [ ] Update documentation to reflect authentication requirements 