---
title: ESPN Basketball Teams API
description: Documentation for ESPN's v3 API endpoint for accessing historical NCAA men's basketball team data across multiple seasons
---

# ESPN Basketball Teams API

## Overview

The ESPN API provides several different ways to access NCAA men's basketball data. While the v2 API (`site.api.espn.com`) is more commonly used and referenced, we've found that it has limitations when trying to access historical team data. This document focuses on the v3 API endpoint which provides access to historical team information across multiple seasons.

## Base URL

```
https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/{season}/teams
```

## Description

This endpoint provides a list of all NCAA men's basketball teams for a specified historical season. It returns basic team metadata including IDs, names, abbreviations, and colors. Unlike the v2 teams endpoint, this endpoint is explicitly season-specific and can access data from past seasons.

## URL Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `{season}` | Required | The season year (e.g., 2020 for the 2019-2020 season) |

## Query Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `limit` | Optional | Number of teams to return per request | 25 |
| `page` | Optional | Page number for pagination | 1 |
| `lang` | Optional | Language for text content | en |
| `region` | Optional | Region code | us |

## Response Format

The response is a JSON object containing:

- `count`: Total number of teams available
- `pageIndex`: Current page number
- `pageSize`: Number of items per page
- `pageCount`: Total number of pages
- `items`: Array of team objects

Each team object contains:
- `id`: Team ID (used in other API calls)
- `uid`: Unique identifier
- `guid`: Global unique identifier
- `slug`: URL-friendly name
- `location`: Team location/university name
- `name`: Team name
- `nickname`: Team nickname (often same as location)
- `abbreviation`: Team shortcode (3-4 letters)
- `displayName`: Full team name
- `shortDisplayName`: Shortened display name
- `color`: Primary color (hex code without #)
- `alternateColor`: Secondary color (hex code without #)
- `active`: Boolean indicating if team is active
- `allstar`: Boolean indicating if team is an all-star team (always false for college teams)

## Sample Usage

```bash
# Get teams from the 2019-2020 season (limit 100 per page)
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2020/teams?limit=100"

# Get page 2 of teams from the 2015-2016 season
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2016/teams?limit=100&page=2"

# Get a specific team (Duke) from the 2018-2019 season
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2019/teams/150"
```

## Sample Response

```json
{
  "count": 355,
  "pageIndex": 1,
  "pageSize": 100,
  "pageCount": 4,
  "items": [
    {
      "id": "2",
      "uid": "s:40~l:41~t:2",
      "guid": "381c82ac-22fb-e25c-879f-6cbf55b5f1e0",
      "slug": "auburn-tigers",
      "location": "Auburn",
      "name": "Tigers",
      "nickname": "Auburn",
      "abbreviation": "AUB",
      "displayName": "Auburn Tigers",
      "shortDisplayName": "Auburn",
      "color": "002b5c",
      "alternateColor": "f26522",
      "active": true,
      "allstar": false
    },
    {
      "id": "6",
      "uid": "s:40~l:41~t:6",
      "guid": "be0a858c-4df7-426d-8386-9292fee10068",
      "slug": "uab-blazers",
      "location": "UAB",
      "name": "Blazers",
      "nickname": "UAB",
      "abbreviation": "UAB",
      "displayName": "UAB Blazers",
      "shortDisplayName": "UAB",
      "color": "054338",
      "alternateColor": "ffc845",
      "active": true,
      "allstar": false
    }
  ]
}
```

## Historical Coverage

- Testing indicates this endpoint provides data back to at least the 2010-2011 season
- Team counts vary by season (ranging from ~340 to ~360 teams)
- Basic team metadata remains consistent across seasons
- No additional performance statistics are included in this endpoint

## Limitations

- This endpoint provides only basic team metadata
- For team statistics, you need to use other endpoints:
  - Team statistics: `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/statistics?season={year}`
  - Team roster: `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster?season={year}`
  - Team schedule: `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/schedule?season={year}`

## Notes

- Unlike some other endpoints, the v3 API requires the season year to be in the URL path rather than as a query parameter
- This is particularly useful for historical analysis as it provides consistent team IDs across seasons
- The v2 API teams endpoint (`/apis/site/v2/sports/basketball/mens-college-basketball/teams`) does not support historical seasons, despite accepting a season parameter