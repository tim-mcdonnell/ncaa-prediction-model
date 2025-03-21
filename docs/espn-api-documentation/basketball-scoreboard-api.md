---
title: ESPN Basketball Scoreboard API
description: Documentation for ESPN's NCAA men's basketball scoreboard API endpoint, with details on retrieving historical game data
---

# ESPN Basketball Scoreboard API

## Overview

The ESPN API provides access to NCAA men's basketball game data including schedules, scores, and detailed game statistics. This document focuses on the v2 API scoreboard endpoint which provides comprehensive game information and can be used to access both current and historical game data.

## Base URL

```
http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard
```

## Description

This endpoint provides detailed information about games for specified dates, including team information, scores, game status, statistics, and more. It can be used to access current or historical game data, making it suitable for retrospective analysis of NCAA men's basketball games.

## Query Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `dates` | Optional | Date or date range in YYYYMMDD format. Can be a single date (20230311) or a range using hyphen (20230101-20230102) | Current date |
| `groups` | Optional | Filter by conference/division group ID (e.g., 50 for Division I, 2 for ACC, etc.) | All games |
| `limit` | Optional | Maximum number of games to return | 25 |
| `lang` | Optional | Language for text content | en |
| `region` | Optional | Region code | us |

## Response Format

The response is a JSON object containing:

- `events`: Array of game objects
- `leagues`: Information about the league (NCAA men's basketball)
- `groups`: Information about the conferences/divisions
- `eventsDate`: Date information for the returned events

Each game in the `events` array includes:
- `id`: Game ID (used in other API calls)
- `uid`: Unique identifier
- `date`: Date and time of the game (ISO format)
- `name`: Full game name (e.g., "UMass Lowell River Hawks at Vermont Catamounts")
- `shortName`: Short game name (e.g., "UML @ UVM")
- `season`: Season information (year, type, slug)
- `competitions`: Array containing detailed game information (typically a single item)

Within each competition:
- `id`: Competition ID
- `date`: Date and time (ISO format)
- `attendance`: Number of attendees
- `venue`: Venue information (name, location)
- `competitors`: Array with information about both teams, including:
  - Team metadata (id, location, name, abbreviation, colors)
  - Score
  - Game statistics (rebounds, assists, field goals, etc.)
  - Team leaders for various categories (points, rebounds, assists)
  - Team records
- `status`: Game status information (time remaining, period, completion status)
- `broadcasts`: TV/streaming broadcast information
- `notes`: Additional game information
- `headlines`: Game recaps and summaries
- `links`: Links to related content (gamecast, box score, highlights, etc.)

## Sample Usage

```bash
# Get games from March 11, 2023 (showing only Division I games, limit 100)
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230311&groups=50&limit=100"

# Get games from January 1-2, 2023
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230101-20230102&groups=50&limit=50"

# Get only ACC games from March 11, 2023
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230311&groups=2&limit=10"
```

## Sample Response

```json
{
  "events": [
    {
      "id": "401522112",
      "uid": "s:40~l:41~e:401522112",
      "date": "2023-03-11T16:00Z",
      "name": "UMass Lowell River Hawks at Vermont Catamounts",
      "shortName": "UML @ UVM",
      "season": {
        "year": 2023,
        "type": 2,
        "slug": "regular-season"
      },
      "competitions": [
        {
          "id": "401522112",
          "uid": "s:40~l:41~e:401522112~c:401522112",
          "date": "2023-03-11T16:00Z",
          "attendance": 2880,
          "type": {
            "id": "6",
            "abbreviation": "TRNMNT"
          },
          "venue": {
            "id": "2118",
            "fullName": "Patrick Gymnasium",
            "address": {
              "city": "Burlington",
              "state": "VT"
            }
          },
          "competitors": [
            {
              "id": "261",
              "type": "team",
              "homeAway": "home",
              "winner": true,
              "team": {
                "id": "261",
                "location": "Vermont",
                "name": "Catamounts",
                "abbreviation": "UVM",
                "displayName": "Vermont Catamounts",
                "color": "143624",
                "alternateColor": "f8c220"
              },
              "score": "72",
              "statistics": [
                {"name": "rebounds", "displayValue": "35"},
                {"name": "assists", "displayValue": "13"},
                {"name": "fieldGoalPct", "displayValue": "47.5"}
              ]
            }
          ],
          "status": {
            "type": {
              "id": "3",
              "name": "STATUS_FINAL",
              "state": "post",
              "completed": true,
              "description": "Final",
              "detail": "Final"
            }
          },
          "broadcasts": [
            {"market": "national", "names": ["ESPN2"]}
          ]
        }
      ]
    }
  ]
}
```

## Historical Coverage

- Testing indicates this endpoint provides data back to at least the 2010-2011 season
- Data availability is most comprehensive for Division I games
- Game details become more limited for older seasons
- Some statistics may not be available for all historical games

## Common Group IDs (Conference Filters)

| Group ID | Conference/Division |
|----------|---------------------|
| 50 | Division I |
| 2 | Atlantic Coast Conference (ACC) |
| 21 | Pacific-12 Conference (Pac-12) |
| 9 | Big West Conference |
| 11 | Conference USA |
| 13 | Metro Atlantic Athletic Conference (MAAC) |
| 30 | Western Athletic Conference (WAC) |
| 5 | Big East Conference |
| 8 | Big Ten Conference |
| 23 | Southeastern Conference (SEC) |
| 62 | Division II |
| 63 | Division III |

## Limitations

- The `limit` parameter caps the number of games returned in a single request
- For dates with many games, multiple requests with pagination may be necessary
- Not all statistical categories are available for every game, especially for older games
- Some game details may be limited for non-Division I games

## Notes

- Dates must be in YYYYMMDD format
- Date ranges are supported using a hyphen (e.g., 20230101-20230102)
- Game times are provided in UTC/GMT (ISO format)
- The `groups` parameter is useful for filtering by conference/division
- Game IDs can be used with other ESPN endpoints to get additional details
