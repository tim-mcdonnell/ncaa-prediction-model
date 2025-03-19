

Start new chat
Projects
Chats
Recents
Untitled
Designing a Scalable Data Pipeline for NCAA Basketball Analytics
Guide to Writing Cursor Rules for Agentic AI Developers
Cursor Rules for Agentic AI Software Development
Restoring a Dried-Out End Grain Cutting Board
Structuring NCAA Basketball Data for Analysis and Prediction
Structuring Data for NCAA Basketball Analysis
Understanding Medallion Data Architecture
College Basketball Tournament Matchups
GitHub .github Directory Purpose and Configuration
High-Level Structure for NCAA Basketball Data Analytics
NCAA Basketball Tournament Data
Understanding Test-Driven Development
Accidentally Committed to Main Branch
Researching Avantor: Preparing for a Potential Job Application
Dragon Ball Kai Episode Links
Integrated Planning Deck Prep
Categorizing WRIN data with confidence ratings
Understanding SPOD in Chain Restaurants
Protecting Your GitHub Main Branch
Weekly Productivity Update for Boss
Stubborn or Entrenched Subordinate
Sustainability Practices in Supply Chain
Analyzing Basketball Data Processing Pipeline
Interview Guide for Forecast Analyst Hire
Choosing Python Dependency Management: Poetry vs. uv
Defining Your Career Goals
Guidelines for an AI Coding Assistant
NCAA Basketball Prediction Project
Pronouncing the Polish Name Elzbieta
View all
Professional plan

TM
tj1627@gmail.com
All projects


March Madness
Private
I'm trying to design a data analytics project to gather data about past ncaa men's basketball games, engineer features and calculate statistics, and then use those to ultimately create different models to predict the outcome of upcoming games.
Show more





3.7 Sonnet

Choose style
March Madness
No file chosen


Untitled
Last message 1 minute ago

Designing a Scalable Data Pipeline for NCAA Basketball Analytics
Last message 1 minute ago

High-Level Structure for NCAA Basketball Data Analytics
Last message 2 days ago

Project knowledge


Set project instructions
Optional
14% of knowledge capacity used

md
FEATURE_ENGINEERING.md
2 days ago


md
docs/index.md
2 days ago


txt
setup_project.sh
2 days ago


md
espn-api-reference
2 days ago
•
Very large file

Claude
espn-api-reference.md

63.36 KB •1,958 lines
Formatting may be inconsistent from source

---
title: ESPN API Integration
description: Documentation for ESPN API endpoints used for NCAA men's basketball data collection
---

# ESPN API Integration Documentation {#introduction}

This document provides information about ESPN's undocumented APIs for NCAA men's basketball data. These endpoints are not officially documented by ESPN and may change without notice.

[TOC]

## Base URLs {#base-urls}
- Primary base URL: `http://site.api.espn.com`
- Alternative base URLs:
  - `https://sports.core.api.espn.com`

## Quick Reference Table {#quick-reference}

| Endpoint | URL Pattern | Historical Data | Parameters | Notes |
|----------|-------------|-----------------|------------|-------|
| **Scoreboard** | `/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` | Yes (2003+) | `dates=YYYYMMDD`, `groups=50` | Date-specific rather than season-specific |
| **Athletes/Players** | `/v3/sports/basketball/mens-college-basketball/athletes` | Yes | Current: none<br>Historical: `/seasons/{year}/athletes` | Two different URL patterns |
| **Team Schedule** | `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/schedule` | Yes | `season=YYYY`, `seasontype=n` | Works for historical seasons |
| **Team Roster** | `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster` | Limited | `season=YYYY` | Limited data before 2020 |
| **Team Statistics** | `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/statistics` | Yes | `season=YYYY` | Single team stats |
| **All Teams Statistics** | `/v3/sports/basketball/mens-college-basketball/statistics` | Yes | `season=YYYY`, `limit=n` | All teams stats |
| **Rankings** | `/apis/site/v2/sports/basketball/mens-college-basketball/rankings` | Yes (2010+) | `season=YYYY` | AP Poll, Coaches Poll, etc. |
| **Standings** | `/apis/site/v2/sports/basketball/mens-college-basketball/standings` | Yes (2010+) | `season=YYYY` | Conference standings |
| **Tournament Bracket** | `/v2/sports/basketball/leagues/mens-college-basketball/tournaments/22/seasons/{season}/bracketology` | Limited | `{season}` in URL | Works through 2021 |
| **Teams List** | `/apis/site/v2/sports/basketball/mens-college-basketball/teams` | Season-agnostic | `page=n`, `limit=n` | All teams information |
| **Single Team** | `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}` | Season-agnostic | `team` | Team metadata |
| **Game Summary** | `/apis/site/v2/sports/basketball/mens-college-basketball/summary` | Season-agnostic | `event=game_id` | Detailed game data |
| **News** | `/apis/site/v2/sports/basketball/mens-college-basketball/news` | Season-agnostic | None | Latest news |
| **Conferences** | `/apis/site/v2/sports/basketball/mens-college-basketball/groups` | Season-agnostic | None | Conference information |

## Historical Data Availability {#historical-data}

Based on research, the ESPN API provides data back to approximately 2003 for NCAA men's basketball. However, there are some considerations:

1. **Data completeness**: More recent seasons (2010 onwards) have more complete data
2. **Play-by-play data**: Available for most games from around 2010 onwards
3. **Older seasons**: May have limited statistics or missing games
4. **Player data**: Historical player data requires using season-specific endpoints

!!! note "Data Verification"
    This documentation was last verified in March 2024. Endpoints may change without notice as these are undocumented APIs.

## Global Parameters {#global-parameters}

Many endpoints support these common parameters:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `limit` | Maximum number of items to return | Varies by endpoint | `limit=100` |
| `groups=50` | **CRITICAL** - Filter to include all Division I games | N/A | `groups=50` |
| `page`/`pageIndex` | Page number for paginated results | 1 | `page=2` |
| `lang` | Language for response text | "en" | `lang=es` |

## Team Data {#team-data}

### Team Metadata {#team-metadata}

#### Teams List {#teams-list}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/teams`
- Season-agnostic endpoint (not tied to a specific season)
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `page=n` | Optional | Get specific page of teams (pagination, 50 teams per page) |
| `limit=n` | Optional | Limit number of results |

- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams?page=1"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "count": 358,
      "pageIndex": 1,
      "pageSize": 50,
      "pageCount": 8,
      "items": [
        {
          "id": "2",
          "uid": "s:40~l:41~t:2",
          "slug": "auburn-tigers",
          "location": "Auburn",
          "name": "Tigers",
          "nickname": "Auburn",
          "abbreviation": "AUB",
          "displayName": "Auburn Tigers",
          "shortDisplayName": "Tigers",
          "color": "03244d",
          "alternateColor": "f26522",
          "isActive": true,
          "isAllStar": false,
          "logos": [
            {
              "href": "https://a.espncdn.com/i/teamlogos/ncaa/500/2.png",
              "width": 500,
              "height": 500,
              "alt": "",
              "rel": ["full", "default"],
              "lastUpdated": "2018-06-05T12:05Z"
            }
          ],
          "links": [
            {
              "language": "en-US",
              "rel": ["clubhouse", "desktop", "team"],
              "href": "https://www.espn.com/mens-college-basketball/team/_/id/2/auburn-tigers",
              "text": "Clubhouse",
              "shortText": "Clubhouse",
              "isExternal": false,
              "isPremium": false
            }
          ]
        },
        // Additional teams omitted for brevity
      ]
    }
    ```

#### Single Team {#single-team}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}`
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `team` | Required | Team ID or abbreviation |

- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/150"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "team": {
        "id": "150",
        "uid": "s:40~l:41~t:150",
        "slug": "duke-blue-devils",
        "location": "Duke",
        "name": "Blue Devils",
        "nickname": "Duke",
        "abbreviation": "DUKE",
        "displayName": "Duke Blue Devils",
        "shortDisplayName": "Blue Devils",
        "color": "001A57",
        "alternateColor": "f1f2f3",
        "isActive": true,
        "isAllStar": false,
        "logos": [
          {
            "href": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png",
            "width": 500,
            "height": 500,
            "alt": "",
            "rel": ["full", "default"],
            "lastUpdated": "2018-06-05T12:05Z"
          }
        ],
        "record": {
          "items": [
            {
              "summary": "27-9",
              "stats": [
                {
                  "name": "playoffSeed",
                  "value": 4
                },
                {
                  "name": "wins",
                  "value": 27
                },
                {
                  "name": "losses",
                  "value": 9
                },
                {
                  "name": "winPercent",
                  "value": 0.75
                },
                {
                  "name": "gamesBehind",
                  "value": 0
                },
                {
                  "name": "ties",
                  "value": 0
                },
                {
                  "name": "OTWins",
                  "value": 0
                },
                {
                  "name": "OTLosses",
                  "value": 0
                },
                {
                  "name": "gamesPlayed",
                  "value": 36
                },
                {
                  "name": "pointsFor",
                  "value": 2639
                },
                {
                  "name": "pointsAgainst",
                  "value": 2347
                },
                {
                  "name": "avgPointsFor",
                  "value": 73.3
                },
                {
                  "name": "avgPointsAgainst",
                  "value": 65.2
                }
              ]
            }
          ]
        },
        "links": [
          {
            "language": "en-US",
            "rel": ["clubhouse", "desktop", "team"],
            "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils",
            "text": "Clubhouse",
            "shortText": "Clubhouse",
            "isExternal": false,
            "isPremium": false
          }
        ],
        "nextEvent": [
          {
            "id": "401514211",
            "date": "2025-03-15T19:00Z",
            "name": "Duke Blue Devils vs. Virginia Cavaliers",
            "shortName": "DUKE vs. UVA",
            "seasonType": {
              "id": "3",
              "type": 3,
              "name": "Postseason",
              "abbreviation": "post"
            },
            "timeValid": true,
            "competitions": [
              {
                "id": "401514211",
                "date": "2025-03-15T19:00Z",
                "venue": {
                  "fullName": "Capital One Arena"
                }
              }
            ]
          }
        ]
      }
    }
    ```

**See also:** [Team Roster](#team-roster), [Team Schedule](#team-schedule)

### Team Roster {#team-roster}
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster`
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `team` | Required | Team ID or abbreviation |
| `season=YYYY` | Optional | Season year (e.g., 2023) |

- **Historical Data Limitations**:
  - Current season (2024): Complete rosters (12-24 players)
  - Previous season (2023): Near-complete rosters (6-12 players)
  - 2021-2022 seasons: Partial rosters (1-6 players)
  - 2020 and earlier: Very limited data (0-1 players or empty)
- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/150/roster?season=2023"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "timestamp": "2025-03-16T21:05:36Z",
      "status": "success",
      "season": {
        "year": 2023,
        "displayName": "2022-23"
      },
      "athletes": [
        {
          "id": "4683735",
          "uid": "s:40~l:41~a:4683735",
          "guid": "f0d1251f68e0d8fe44f81c3034e7ff4a",
          "firstName": "Jaylen",
          "lastName": "Blakes",
          "fullName": "Jaylen Blakes",
          "displayName": "Jaylen Blakes",
          "shortName": "J. Blakes",
          "weight": 208,
          "displayWeight": "208 lbs",
          "height": 74,
          "displayHeight": "6' 2\"",
          "age": 21,
          "dateOfBirth": "2002-12-18",
          "links": [
            {
              "rel": ["playercard", "desktop", "athlete"],
              "href": "https://www.espn.com/mens-college-basketball/player/_/id/4683735/jaylen-blakes"
            },
            {
              "rel": ["stats", "desktop", "athlete"],
              "href": "http://www.espn.com/mens-college-basketball/player/stats/_/id/4683735/jaylen-blakes"
            },
            {
              "rel": ["bio", "desktop", "athlete"],
              "href": "http://www.espn.com/mens-college-basketball/player/bio/_/id/4683735/jaylen-blakes"
            }
          ],
          "headshot": {
            "href": "https://a.espncdn.com/i/headshots/mens-college-basketball/players/full/4683735.png",
            "alt": "Jaylen Blakes"
          },
          "jersey": "21",
          "position": {
            "id": "3",
            "name": "Guard",
            "displayName": "Guard",
            "abbreviation": "G",
            "displayValue": "Guard"
          },
          "status": {
            "id": "active",
            "name": "Active",
            "type": "active"
          },
          "experience": {
            "years": 3,
            "displayValue": "Junior"
          },
          "birthPlace": {
            "city": "Somerset",
            "state": "New Jersey",
            "country": "USA"
          }
        }
      ],
      "coach": [
        {
          "id": "31709",
          "firstName": "Jon",
          "lastName": "Scheyer",
          "experience": 1
        }
      ],
      "team": {
        "id": "150",
        "uid": "s:40~l:41~t:150",
        "slug": "duke-blue-devils",
        "location": "Duke",
        "name": "Blue Devils",
        "nickname": "Duke",
        "abbreviation": "DUKE",
        "displayName": "Duke Blue Devils",
        "shortDisplayName": "Blue Devils",
        "color": "001A57",
        "alternateColor": "f1f2f3",
        "logos": [
          {
            "href": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png",
            "width": 500,
            "height": 500,
            "alt": "",
            "rel": ["full", "default"],
            "lastUpdated": "2018-06-05T12:05Z"
          }
        ],
        "recordSummary": "27-9",
        "links": [
          {
            "language": "en-US",
            "rel": ["clubhouse", "desktop", "team"],
            "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils",
            "text": "Clubhouse",
            "shortText": "Clubhouse",
            "isExternal": false,
            "isPremium": false
          }
        ],
        "standingSummary": "Finished 5th in ACC",
        "seasonSummary": "2022-23"
      }
    }
    ```

**See also:** [Player Data](#player-data), [Team Statistics](#team-statistics)

### Team Schedule {#team-schedule}
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/schedule`
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `team` | Required | Team ID or abbreviation |
| `season=YYYY` | Optional | Season year (e.g., 2024) |
| `seasontype=n` | Optional | Season type (2=regular, 3=postseason) |

- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/150/schedule?season=2023"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "timestamp": "2025-03-16T21:05:36Z",
      "status": "success",
      "season": {
        "year": 2023,
        "displayName": "2022-23"
      },
      "count": 36,
      "pageIndex": 1,
      "pageCount": 1,
      "pageSize": 36,
      "items": [
        {
          "id": "401468042",
          "date": "2022-11-07T23:30Z",
          "name": "Jacksonville Dolphins at Duke Blue Devils",
          "shortName": "JAC @ DUKE",
          "season": {
            "year": 2023,
            "type": 2,
            "slug": "regular-season",
            "displayName": "Regular Season"
          },
          "seasonType": {
            "id": "2",
            "type": 2,
            "name": "Regular Season",
            "abbreviation": "reg"
          },
          "week": {
            "number": 1
          },
          "competitions": [
            {
              "id": "401468042",
              "date": "2022-11-07T23:30Z",
              "attendance": 9314,
              "type": {
                "id": "1",
                "text": "Standard",
                "abbreviation": "STD",
                "slug": "standard"
              },
              "timeValid": true,
              "neutralSite": false,
              "conferenceCompetition": false,
              "playByPlayAvailable": true,
              "commentaryAvailable": true,
              "recent": false,
              "venue": {
                "id": "3982",
                "fullName": "Cameron Indoor Stadium",
                "address": {
                  "city": "Durham",
                  "state": "NC"
                },
                "capacity": 9314,
                "indoor": true
              },
              "competitors": [
                {
                  "id": "150",
                  "type": "team",
                  "order": 0,
                  "homeAway": "home",
                  "winner": true,
                  "score": {
                    "value": 71
                  },
                  "statistics": [],
                  "leaders": [
                    {
                      "name": "points",
                      "displayName": "Points",
                      "shortDisplayName": "Pts",
                      "abbreviation": "Pts",
                      "leaders": [
                        {
                          "displayValue": "22",
                          "value": 22.0,
                          "athlete": {
                            "id": "5161857",
                            "displayName": "Mark Mitchell"
                          },
                          "team": {
                            "id": "150"
                          }
                        }
                      ]
                    }
                  ],
                  "team": {
                    "id": "150",
                    "location": "Duke",
                    "nickname": "Blue Devils",
                    "abbreviation": "DUKE",
                    "displayName": "Duke Blue Devils",
                    "shortDisplayName": "Blue Devils",
                    "color": "001A57",
                    "alternateColor": "f1f2f3",
                    "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png"
                  },
                  "curatedRank": {
                    "current": 7
                  },
                  "records": [
                    {
                      "name": "overall",
                      "abbreviation": "overall",
                      "type": "total",
                      "summary": "1-0"
                    }
                  ],
                  "alerts": []
                },
                {
                  "id": "294",
                  "type": "team",
                  "order": 1,
                  "homeAway": "away",
                  "winner": false,
                  "score": {
                    "value": 44
                  },
                  "statistics": [],
                  "leaders": [
                    {
                      "name": "points",
                      "displayName": "Points",
                      "shortDisplayName": "Pts",
                      "abbreviation": "Pts",
                      "leaders": [
                        {
                          "displayValue": "12",
                          "value": 12.0,
                          "athlete": {
                            "id": "4592446",
                            "displayName": "Kevion Nolan"
                          },
                          "team": {
                            "id": "294"
                          }
                        }
                      ]
                    }
                  ],
                  "team": {
                    "id": "294",
                    "location": "Jacksonville",
                    "nickname": "Dolphins",
                    "abbreviation": "JAC",
                    "displayName": "Jacksonville Dolphins",
                    "shortDisplayName": "Dolphins",
                    "color": "004e27",
                    "alternateColor": "a6abab",
                    "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/294.png"
                  },
                  "curatedRank": {},
                  "records": [
                    {
                      "name": "overall",
                      "abbreviation": "overall",
                      "type": "total",
                      "summary": "0-1"
                    }
                  ],
                  "alerts": []
                }
              ],
              "notes": [],
              "status": {
                "type": {
                  "id": "3",
                  "name": "STATUS_FINAL",
                  "state": "post",
                  "completed": true,
                  "description": "Final",
                  "detail": "Final",
                  "shortDetail": "Final"
                },
                "clock": 0,
                "displayClock": "0:00",
                "period": 2,
                "featuredAthletes": []
              },
              "links": [
                {
                  "language": "en-US",
                  "rel": ["summary", "desktop", "event"],
                  "href": "https://www.espn.com/mens-college-basketball/game/_/gameId/401468042",
                  "text": "Box Score",
                  "shortText": "Box Score",
                  "isExternal": false,
                  "isPremium": false
                },
                {
                  "language": "en-US",
                  "rel": ["recap", "desktop", "event"],
                  "href": "https://www.espn.com/mens-college-basketball/recap/_/gameId/401468042",
                  "text": "Recap",
                  "shortText": "Recap",
                  "isExternal": false,
                  "isPremium": false
                }
              ],
              "broadcasts": [],
              "groups": {
                "id": "50",
                "name": "Division I",
                "shortName": "Division I",
                "isConference": false
              }
            }
          ],
          "links": [
            {
              "language": "en-US",
              "rel": ["summary", "desktop", "event"],
              "href": "https://www.espn.com/mens-college-basketball/game/_/gameId/401468042",
              "text": "Box Score",
              "shortText": "Box Score",
              "isExternal": false,
              "isPremium": false
            }
          ],
          "status": {
            "type": {
              "id": "3",
              "name": "STATUS_FINAL",
              "state": "post",
              "completed": true,
              "description": "Final",
              "detail": "Final",
              "shortDetail": "Final"
            },
            "clock": 0,
            "displayClock": "0:00",
            "period": 2,
            "featuredAthletes": []
          }
        }
      ]
    }
    ```

**See also:** [Game Summary](#game-summary), [Scoreboard](#scoreboard)

### Team Statistics {#team-statistics}

#### Current Season Team Stats {#single-team-stats}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/statistics`
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `team` | Required | Team ID |
| `season=YYYY` | Optional | Season year (e.g., 2023) for historical statistics |

- Historical data available for past seasons
- Example curl for current season:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/150/statistics"
```
- Example curl for historical season:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/150/statistics?season=2023"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "season": {
        "year": 2025,
        "displayName": "2024-25",
        "type": 2,
        "name": "Regular Season"
      },
      "team": {
        "id": "150",
        "uid": "s:40~l:41~t:150",
        "slug": "duke-blue-devils",
        "abbreviation": "DUKE",
        "displayName": "Duke Blue Devils",
        "shortDisplayName": "Blue Devils",
        "name": "Blue Devils",
        "location": "Duke",
        "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png",
        "recordSummary": "27-9"
      },
      "statistics": [
        {
          "name": "rebounds",
          "displayName": "Rebounds",
          "shortDisplayName": "Reb",
          "description": "Rebounds",
          "abbreviation": "Reb",
          "value": 38.7,
          "displayValue": "38.7"
        },
        {
          "name": "assists",
          "displayName": "Assists",
          "shortDisplayName": "Ast",
          "description": "Assists",
          "abbreviation": "Ast",
          "value": 14.1,
          "displayValue": "14.1"
        },
        {
          "name": "threePointFieldGoalPct",
          "displayName": "3-Point FG%",
          "shortDisplayName": "3P%",
          "description": "3-Point Field Goal Percentage",
          "abbreviation": "3P%",
          "value": 34.9,
          "displayValue": "34.9"
        },
        {
          "name": "freeThrowPct",
          "displayName": "Free Throw Percentage",
          "shortDisplayName": "FT%",
          "description": "Free Throw Percentage",
          "abbreviation": "FT%",
          "value": 77.0,
          "displayValue": "77.0"
        },
        {
          "name": "points",
          "displayName": "Points",
          "shortDisplayName": "Pts",
          "description": "Points",
          "abbreviation": "Pts",
          "value": 2466,
          "displayValue": "2466"
        },
        {
          "name": "fieldGoalPct",
          "displayName": "Field Goal Percentage",
          "shortDisplayName": "FG%",
          "description": "Field Goal Percentage",
          "abbreviation": "FG%",
          "value": 45.1,
          "displayValue": "45.1"
        },
        {
          "name": "steals",
          "displayName": "Steals",
          "shortDisplayName": "Stl",
          "description": "Steals",
          "abbreviation": "Stl",
          "value": 5.7,
          "displayValue": "5.7"
        },
        {
          "name": "blocks",
          "displayName": "Blocks",
          "shortDisplayName": "Blk",
          "description": "Blocks",
          "abbreviation": "Blk",
          "value": 4.5,
          "displayValue": "4.5",
          "rankDisplayValue": "19th"
        },
        {
          "name": "pointsPerGame",
          "displayName": "Points Per Game",
          "shortDisplayName": "PPG",
          "description": "Points Per Game",
          "abbreviation": "PPG",
          "value": 72.5,
          "displayValue": "72.5"
        },
        {
          "name": "totalTurnovers",
          "displayName": "Turnovers",
          "shortDisplayName": "TO",
          "description": "Turnovers",
          "abbreviation": "TO",
          "value": 11.7,
          "displayValue": "11.7"
        }
      ]
    }
    ```

**See also:** [Team Roster](#team-roster)

#### All Teams Statistics {#all-teams-stats}
- URL: `/v3/sports/basketball/mens-college-basketball/statistics`
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `limit=n` | Optional | Limit number of results (default: 25) |
| `page=n` | Optional | Page number for pagination |
| `season=YYYY` | Optional | Season year (e.g., 2023) for historical statistics |

- Historical data available for past seasons
- Example curl for current season:
```bash
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/statistics?limit=100"
```
- Example curl for historical season:
```bash
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/statistics?season=2023&limit=100"
```

??? example "Example Response (truncated)"
    ```json
    {
      "count": 571,
      "pageIndex": 1,
      "pageSize": 5,
      "pageCount": 115,
      "items": [
        {
          "id": "2",
          "type": "team",
          "statistics": {
            "general": {
              "rebounds": {"value": 1158.0, "qualified": true},
                "assistTurnoverRatio": {"value": 1.8204225}
            },
            "offensive": {
              "fieldGoalPct": {"value": 0.4851948, "qualified": true},
                "points": {"value": 2640.0}
            },
            "defensive": {
              "blocks": {"value": 198.0, "qualified": true},
                "steals": {"value": 218.0}
              }
            }
          }
      ]
    }
    ```

**See also:** [Team Roster](#team-roster)

## Game Data {#game-data}

### Scoreboard {#scoreboard}
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`
- Date-based, indirectly season-specific
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `dates=YYYYMMDD` | Optional | Specific date in YYYYMMDD format |
| `groups=50` | **Critical** | Filter to include all Division I games |
| `limit=n` | Optional | Limit number of results (default: 100) |

- Historical data available from approximately 2003
- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230311&groups=50&limit=100"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "leagues": [
        {
          "id": "41",
          "uid": "s:40~l:41",
          "name": "NCAA Men's Basketball",
          "abbreviation": "NCAAM",
          "slug": "mens-college-basketball",
          "season": {
            "year": 2023,
            "startDate": "2022-11-07T08:00Z",
            "endDate": "2023-04-04T04:00Z",
            "type": {
              "id": "2",
              "type": 2,
              "name": "Regular Season",
              "abbreviation": "reg"
            }
          },
          "calendarType": "day",
          "calendarIsWhitelist": true,
          "calendarStartDate": "2022-11-07T08:00Z",
          "calendarEndDate": "2023-04-04T04:00Z",
          "calendar": [
            "20230311"
          ]
        }
      ],
      "season": {
        "type": 2,
        "year": 2023
      },
      "day": {
        "date": "20230311"
      },
      "events": [
        {
          "id": "401499491",
          "uid": "s:40~l:41~e:401499491",
          "date": "2023-03-11T17:00Z",
          "name": "Iona Gaels vs. Marist Red Foxes",
          "shortName": "IONA vs. MRST",
          "season": {
            "year": 2023,
            "type": 3,
            "slug": "postseason"
          },
          "competitions": [
            {
              "id": "401499491",
              "uid": "s:40~l:41~e:401499491~c:401499491",
              "date": "2023-03-11T17:00Z",
              "attendance": 0,
              "type": {
                "id": "1",
                "abbreviation": "STD"
              },
              "timeValid": true,
              "neutralSite": true,
              "conferenceCompetition": true,
              "playByPlayAvailable": true,
              "recent": false,
              "venue": {
                "id": "1964",
                "fullName": "Boardwalk Hall"
              },
              "competitors": [
                {
                  "id": "314",
                  "uid": "s:40~l:41~t:314",
                  "type": "team",
                  "order": 0,
                  "homeAway": "home",
                  "winner": true,
                  "score": "76",
                  "statistics": [],
                  "leaders": [
                    {
                      "name": "points",
                      "displayName": "Points",
                      "leaders": [
                        {
                          "displayValue": "20",
                          "value": 20,
                          "athlete": {
                            "id": "4432609",
                            "fullName": "Walter Clayton Jr.",
                            "displayName": "Walter Clayton Jr.",
                            "shortName": "W. Clayton Jr.",
                            "links": [
                              {
                                "rel": ["playercard", "desktop", "athlete"],
                                "href": "https://www.espn.com/mens-college-basketball/player/_/id/4432609/walter-clayton-jr"
                              }
                            ]
                          },
                          "team": {
                            "id": "314"
                          }
                        }
                      ]
                    }
                  ],
                  "team": {
                    "id": "314",
                    "uid": "s:40~l:41~t:314",
                    "location": "Iona",
                    "name": "Gaels",
                    "abbreviation": "IONA",
                    "displayName": "Iona Gaels",
                    "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/314.png"
                  },
                  "records": [
                    {
                      "name": "overall",
                      "abbreviation": "Game",
                      "type": "total",
                      "summary": "27-7"
                    }
                  ]
                },
                {
                  "id": "2368",
                  "uid": "s:40~l:41~t:2368",
                  "type": "team",
                  "order": 1,
                  "homeAway": "away",
                  "winner": false,
                  "score": "55",
                  "statistics": [],
                  "leaders": [
                    {
                      "name": "points",
                      "displayName": "Points",
                      "leaders": [
                        {
                          "displayValue": "13",
                          "value": 13,
                          "athlete": {
                            "id": "4433076",
                            "fullName": "Patrick Gardner",
                            "displayName": "Patrick Gardner",
                            "shortName": "P. Gardner",
                            "links": [
                              {
                                "rel": ["playercard", "desktop", "athlete"],
                                "href": "https://www.espn.com/mens-college-basketball/player/_/id/4433076/patrick-gardner"
                              }
                            ]
                          },
                          "team": {
                            "id": "2368"
                          }
                        }
                      ]
                    }
                  ],
                  "team": {
                    "id": "2368",
                    "uid": "s:40~l:41~t:2368",
                    "location": "Marist",
                    "name": "Red Foxes",
                    "abbreviation": "MRST",
                    "displayName": "Marist Red Foxes",
                    "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2368.png"
                  },
                  "records": [
                    {
                      "name": "overall",
                      "abbreviation": "Game",
                      "type": "total",
                      "summary": "13-20"
                    }
                  ]
                }
              ],
              "notes": [],
              "status": {
                "clock": 0,
                "displayClock": "0:00",
                "period": 2,
                "type": {
                  "id": "3",
                  "name": "STATUS_FINAL",
                  "state": "post",
                  "completed": true,
                  "description": "Final",
                  "detail": "Final",
                  "shortDetail": "Final"
                }
              },
              "broadcasts": [],
              "format": {
                "regulation": {
                  "periods": 2
                }
              },
              "startDate": "2023-03-11T17:00Z",
              "geoBroadcasts": [],
              "headlines": [
                {
                  "shortLinkText": "Iona wins 76-55 against Marist",
                  "description": "— ATLANTIC CITY, N.J. — Walter Clayton Jr.'s 20 points helped Iona defeat Marist 76-55 in the Metro Atlantic Athletic Conference Tournament semifinals on Saturday."
                }
              ]
            }
          ],
          "status": {
            "clock": 0,
            "displayClock": "0:00",
            "period": 2,
            "type": {
              "id": "3",
              "name": "STATUS_FINAL",
              "state": "post",
              "completed": true,
              "description": "Final",
              "detail": "Final",
              "shortDetail": "Final"
            }
          }
        }
      ]
    }
    ```

**See also:** [Game Summary](#game-summary), [Team Schedule](#team-schedule)

### Game Summary {#game-summary}
- URL: `http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary`
- Season-agnostic endpoint
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `event=game_id` | Required | Game ID (e.g., "401479672") |

- Retrieves detailed game information by game ID
- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event=401514211"
```

??? example "Example Response (real data, key sections)"
    ```json
    {
      "header": {
        "id": "401514211",
        "uid": "s:40~l:41~e:401514211",
        "season": {
          "year": 2025,
          "type": 3,
          "slug": "postseason"
        },
        "timeValid": true,
        "competitions": [
          {
            "id": "401514211",
            "uid": "s:40~l:41~e:401514211~c:401514211",
            "date": "2025-03-15T19:00Z",
            "neutralSite": true,
            "conferenceCompetition": true,
            "boxscoreAvailable": true,
            "commentaryAvailable": true,
            "liveAvailable": true,
            "onWatchESPN": true,
            "recent": false,
            "wasSuspended": false,
            "statusName": "STATUS_FINAL",
            "competitors": [
              {
                "id": "150",
                "uid": "s:40~l:41~t:150",
                "type": "team",
                "order": 0,
                "homeAway": "home",
                "winner": true,
                "score": "59",
                "curatedRank": {
                  "current": 1
                },
                "team": {
                  "id": "150",
                  "uid": "s:40~l:41~t:150",
                  "location": "Duke",
                  "name": "Blue Devils",
                  "nickname": "Duke",
                  "abbreviation": "DUKE",
                  "displayName": "Duke Blue Devils",
                  "color": "001A57"
                }
              },
              {
                "id": "258",
                "uid": "s:40~l:41~t:258",
                "type": "team",
                "order": 1,
                "homeAway": "away",
                "winner": false,
                "score": "49",
                "curatedRank": {
                  "current": 10
                },
                "team": {
                  "id": "258",
                  "uid": "s:40~l:41~t:258",
                  "location": "Virginia",
                  "name": "Cavaliers",
                  "nickname": "Virginia",
                  "abbreviation": "UVA",
                  "displayName": "Virginia Cavaliers",
                  "color": "00204e"
                }
              }
            ]
          }
        ]
      },
      "scoringPlays": [
        {
          "id": "401514211318",
          "type": {
            "id": "2",
            "text": "Made Shot",
            "abbreviation": "MDS"
          },
          "text": "Kyle Filipowski made Jumper.",
          "awayScore": 0,
          "homeScore": 2,
          "period": {
            "number": 1
          },
          "clock": {
            "displayValue": "19:27"
          },
          "scoringType": {
            "name": "field-goal",
            "displayName": "Field Goal",
            "abbreviation": "FG"
          },
          "scoringTeam": {
            "id": "150"
          },
          "shootingPlay": true,
          "coordinate": {
            "x": 51,
            "y": 11
          }
        }
      ],
      "boxscore": {
        "teams": [
          {
            "team": {
              "id": "150",
              "uid": "s:40~l:41~t:150",
              "displayName": "Duke Blue Devils"
            },
            "statistics": [
              {
                "name": "rebounds",
                "displayValue": "32",
                "label": "Rebounds"
              },
              {
                "name": "fieldGoalsAttempted",
                "displayValue": "41",
                "label": "FGA"
              },
              {
                "name": "fieldGoalsMade",
                "displayValue": "22",
                "label": "FGM"
              },
              {
                "name": "fieldGoalPct",
                "displayValue": "53.7",
                "label": "FG%"
              },
              {
                "name": "threePointFieldGoalsAttempted",
                "displayValue": "21",
                "label": "3PA"
              },
              {
                "name": "threePointFieldGoalsMade",
                "displayValue": "6",
                "label": "3PM"
              },
              {
                "name": "threePointFieldGoalPct",
                "displayValue": "28.6",
                "label": "3P%"
              },
              {
                "name": "freeThrowsAttempted",
                "displayValue": "12",
                "label": "FTA"
              },
              {
                "name": "freeThrowsMade",
                "displayValue": "9",
                "label": "FTM"
              },
              {
                "name": "freeThrowPct",
                "displayValue": "75.0",
                "label": "FT%"
              },
              {
                "name": "assists",
                "displayValue": "8",
                "label": "AST"
              },
              {
                "name": "steals",
                "displayValue": "4",
                "label": "STL"
              },
              {
                "name": "blocks",
                "displayValue": "5",
                "label": "BLK"
              },
              {
                "name": "totalTurnovers",
                "displayValue": "12",
                "label": "TO"
              },
              {
                "name": "fouls",
                "displayValue": "10",
                "label": "FOULS"
              }
            ]
          }
        ],
        "players": [
          {
            "team": {
              "id": "150",
              "uid": "s:40~l:41~t:150"
            },
            "statistics": [
              {
                "names": [
                  "minsPlayed",
                  "fieldGoalsMade",
                  "fieldGoalsAttempted",
                  "fieldGoalPct",
                  "threePointMade",
                  "threePointAttempted",
                  "threePointPct",
                  "freeThrowsMade",
                  "freeThrowsAttempted",
                  "freeThrowPct",
                  "reboundsOffensive",
                  "reboundsDefensive",
                  "reboundsTotal",
                  "assists",
                  "steals",
                  "blocks",
                  "turnovers",
                  "foulsPersonal",
                  "points",
                  "plusMinus"
                ],
                "totals": [
                  200,
                  22,
                  41,
                  0.5365853,
                  6,
                  21,
                  0.2857143,
                  9,
                  12,
                  0.75,
                  5,
                  27,
                  32,
                  8,
                  4,
                  5,
                  12,
                  10,
                  59,
                  10
                ],
                "athletes": [
                  {
                    "athlete": {
                      "id": "5203685",
                      "uid": "s:40~l:41~a:5203685",
                      "guid": "2cf33fe2-4a92-3188-9d87-78ac5aac53be",
                      "displayName": "Khaman Maluach",
                      "shortName": "K. Maluach",
                      "active": true,
                      "headshot": {
                        "href": "https://a.espncdn.com/i/headshots/mens-college-basketball/players/full/5203685.png",
                        "alt": "Khaman Maluach"
                      },
                      "position": {
                        "abbreviation": "C"
                      },
                      "jersey": "15",
                      "links": [
                        {
                          "rel": ["playercard", "desktop", "athlete"],
                          "href": "https://www.espn.com/mens-college-basketball/player/_/id/5203685/khaman-maluach"
                        }
                      ]
                    },
                    "starter": true,
                    "didNotPlay": false,
                    "reason": null,
                    "stats": [
                      "29",
                      "6",
                      "9",
                      ".667",
                      "0",
                      "0",
                      ".000",
                      "3",
                      "3",
                      "1.000",
                      "1",
                      "9",
                      "10",
                      "0",
                      "2",
                      "2",
                      "0",
                      "0",
                      "15",
                      "4"
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    }
    ```

**See also:** [Scoreboard](#scoreboard)

### Tournament Bracket {#tournament-bracket}
- URL: `/v2/sports/basketball/leagues/mens-college-basketball/tournaments/22/seasons/{season}/bracketology`
- Explicitly season-specific
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `{season}` | Required | Season year (e.g., 2021) |

- Reports indicate this works for years up to 2021
- Example curl:
```bash
curl "http://site.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/tournaments/22/seasons/2021/bracketology"
```

## Rankings & Standings {#rankings-standings}

### Rankings {#rankings}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/rankings`
- Defaults to current season rankings
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `season=YYYY` | Optional | Season year (e.g., 2023) for historical rankings |

- Historical data available back to at least 2010
- Example curl for current rankings:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
```
- Example curl for historical rankings:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings?season=2023"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "rankings": [
        {
          "id": 1,
          "name": "AP Top 25",
          "abbreviation": "AP",
          "type": "ap_poll",
          "headline": "2024-25 AP Poll",
          "shortHeadline": "AP Poll 2025",
          "pollData": {
            "seasonId": 2025,
            "seasonName": "2024-25",
            "seasonYear": 2025,
            "updateDate": "2025-03-10T17:00:00Z",
            "currentWeek": 19,
            "finalWeek": true
          },
          "ranks": [
            {
              "current": 1,
              "previous": 1,
              "trend": 0,
              "points": 1600,
              "firstPlaceVotes": 64,
              "lastUpdated": "2025-03-10T17:00:00Z",
              "moreStats": {
                "rank": 1,
                "week": 19,
                "rankChange": 0
              },
              "team": {
                "id": "150",
                "uid": "s:40~l:41~t:150",
                "location": "Duke",
                "name": "Blue Devils",
                "abbreviation": "DUKE",
                "displayName": "Duke Blue Devils",
                "clubhouse": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils",
                "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/150.png",
                "logoDark": "https://a.espncdn.com/i/teamlogos/ncaa/500-dark/150.png",
                "links": [
                  {
                    "rel": ["clubhouse", "desktop", "team"],
                    "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils",
                    "text": "Clubhouse"
                  }
                ]
              }
            },
            {
              "current": 2,
              "previous": 2,
              "trend": 0,
              "points": 1535,
              "firstPlaceVotes": 0,
              "lastUpdated": "2025-03-10T17:00:00Z",
              "moreStats": {
                "rank": 2,
                "week": 19,
                "rankChange": 0
              },
              "team": {
                "id": "248",
                "uid": "s:40~l:41~t:248",
                "location": "Houston",
                "name": "Cougars",
                "abbreviation": "HOU",
                "displayName": "Houston Cougars",
                "clubhouse": "https://www.espn.com/mens-college-basketball/team/_/id/248/houston-cougars",
                "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/248.png",
                "logoDark": "https://a.espncdn.com/i/teamlogos/ncaa/500-dark/248.png",
                "links": [
                  {
                    "rel": ["clubhouse", "desktop", "team"],
                    "href": "https://www.espn.com/mens-college-basketball/team/_/id/248/houston-cougars",
                    "text": "Clubhouse"
                  }
                ]
              }
            },
            {
              "current": 3,
              "previous": 3,
              "trend": 0,
              "points": 1465,
              "firstPlaceVotes": 0,
              "lastUpdated": "2025-03-10T17:00:00Z",
              "moreStats": {
                "rank": 3,
                "week": 19,
                "rankChange": 0
              },
              "team": {
                "id": "2",
                "uid": "s:40~l:41~t:2",
                "location": "Auburn",
                "name": "Tigers",
                "abbreviation": "AUB",
                "displayName": "Auburn Tigers",
                "clubhouse": "https://www.espn.com/mens-college-basketball/team/_/id/2/auburn-tigers",
                "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2.png",
                "logoDark": "https://a.espncdn.com/i/teamlogos/ncaa/500-dark/2.png",
                "links": [
                  {
                    "rel": ["clubhouse", "desktop", "team"],
                    "href": "https://www.espn.com/mens-college-basketball/team/_/id/2/auburn-tigers",
                    "text": "Clubhouse"
                  }
                ]
              }
            }
          ]
        }
      ]
    }
    ```

### Standings {#standings}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/standings`
- Alternative URL: `https://site.web.api.espn.com/apis/v2/sports/basketball/mens-college-basketball/standings`
- Defaults to current season standings
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `season=YYYY` | Optional | Season year (e.g., 2023) for historical standings |
| `region=us&lang=en&contentorigin=espn` | Optional | Additional parameters for alternative URL |

- Historical data available back to at least 2010
- Example curl for current standings:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/standings"
```
- Example curl for historical standings:
```bash
curl "https://site.web.api.espn.com/apis/v2/sports/basketball/mens-college-basketball/standings?region=us&lang=en&contentorigin=espn&season=2023"
```

## Player Data {#player-data}

### Current Season Athletes {#current-athletes}
- URL: `/v3/sports/basketball/mens-college-basketball/athletes`
- Defaults to current season
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `limit=n` | Optional | Limit number of results (default: 25, can set high value like 10000) |

- Example curl:
```bash
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/athletes?limit=10000"
```

### Historical Athletes {#historical-athletes}
- URL: `/v3/sports/basketball/mens-college-basketball/seasons/{year}/athletes`
- Explicitly requires season year in URL
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `{year}` | Required | Season year in URL path |
| `limit=n` | Optional | Limit number of results |

- Example curl:
```bash
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/seasons/2023/athletes?limit=1000"
```

### Individual Player Details {#player-details}
- URL: `/v3/sports/basketball/mens-college-basketball/athletes/{playerID}`
- Retrieves detailed data for specific player
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `{playerID}` | Required | Player ID in URL path |

- Example curl:
```bash
curl "https://sports.core.api.espn.com/v3/sports/basketball/mens-college-basketball/athletes/5158125"
```

??? example "Example Response (truncated)"
    ```json
    {
      "id": "5158125",
      "guid": "f75b0cea22c5e38b90efff8f15386271",
      "uid": "s:40~l:41~a:5158125",
      "type": "athlete",
      "firstName": "TJ",
      "lastName": "Power",
      "fullName": "TJ Power",
      "displayName": "TJ Power",
      "shortName": "T. Power",
      "weight": 210,
      "displayWeight": "210 lbs",
      "height": 81,
      "displayHeight": "6' 9\"",
      "age": 19,
      "jersey": "0",
                      "position": {
        "id": 5,
        "name": "Forward",
        "displayName": "Forward",
        "abbreviation": "F"
      }
    }
    ```

**See also:** [Team Roster](#team-roster)

## Other Endpoints {#other-endpoints}

### News Endpoint {#news}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/news`
- Retrieves latest news, not season-specific
- Parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `team` | Optional | Team ID to filter news for a specific team |

- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/news"
```
- Example curl for team-specific news:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/news?team=150"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "header": "Men's College Basketball News",
      "link": {
        "language": "en",
        "rel": ["index", "desktop", "league"],
        "href": "https://www.espn.com/mens-college-basketball/",
        "text": "All NCAAM News",
        "shortText": "All News",
        "isExternal": false,
        "isPremium": false
      },
      "articles": [
        {
          "dataSourceIdentifier": "49558377fabf1",
          "type": "Story",
          "headline": "Men's Champ Week 2025: tournament schedules, auto-bids, more",
          "description": "We tracked all 31 men's college basketball conference tournaments including every automatic bid winner in the lead up to March Madness.",
          "lastModified": "2025-03-16T21:39:40Z",
          "published": "2025-03-16T21:39:00Z",
          "images": [
            {
              "dataSourceIdentifier": "db5856cf6a333",
              "id": 44262983,
              "type": "header",
              "name": "American University 2025 ticket punched [1296x729]",
              "caption": "American University is returning to the NCAA tournament for the first time since 2014, after defeating Navy in the Patriot League title game.",
              "credit": "AP Photo/Terrance Williams",
              "height": 729,
              "width": 1296,
              "url": "https://a.espncdn.com/photo/2025/0315/r1464565_1296x729_16-9.jpg"
            }
          ],
          "categories": [
            {
              "id": 3155,
              "type": "team",
              "uid": "s:40~l:41~t:150",
              "guid": "c4430c6c-5998-47d5-7c45-1cdb7ca0befc",
              "description": "Duke Blue Devils",
              "sportId": 41,
              "teamId": 150,
              "team": {
                "id": 150,
                "description": "Duke Blue Devils",
                "links": {
                  "web": {
                    "teams": {
                      "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils"
                    }
                  },
                  "mobile": {
                    "teams": {
                      "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils"
                    }
                  }
                }
              }
            }
          ],
          "premium": false,
          "links": {
            "web": {
              "href": "https://www.espn.com/mens-college-basketball/story/_/id/43734580/mens-college-basketball-champ-week-2025-tournament-brackets-schedule-sites-bids-stats-history"
            },
            "mobile": {
              "href": "http://m.espn.go.com/wireless/story?storyId=43734580"
            },
            "api": {
              "self": {
                "href": "https://content.core.api.espn.com/v1/sports/news/43734580"
              }
            },
            "app": {
              "sportscenter": {
                "href": "sportscenter://x-callback-url/showStory?uid=43734580"
              }
            }
          },
          "byline": "ESPN"
        },
        {
          "dataSourceIdentifier": "881068e715fdd",
          "type": "Eticket",
          "headline": "NCAA Bracketology: 2025 March Madness men's field predictions",
          "description": "There's little any team can do now about its chances, so take a look at the final projected NCAA tournament field for 2025. Watch the men's bracket reveal starting at 6 p.m. ET on ESPN.",
          "lastModified": "2025-03-16T21:58:48Z",
          "published": "2025-03-16T07:00:00Z",
          "images": [
            {
              "dataSourceIdentifier": "51b04a33bb1c2",
              "id": 44226841,
              "type": "header",
              "name": "Tre Johnson [1296x729]",
              "credit": "Petre Thomas-Imagn Images",
              "height": 729,
              "width": 1296,
              "url": "https://a.espncdn.com/photo/2025/0313/r1463379_1296x729_16-9.jpg"
            }
          ],
          "categories": [
            {
              "id": 3155,
              "type": "team",
              "uid": "s:40~l:41~t:150",
              "guid": "c4430c6c-5998-47d5-7c45-1cdb7ca0befc",
              "description": "Duke Blue Devils",
              "sportId": 41,
              "teamId": 150,
              "team": {
                "id": 150,
                "description": "Duke Blue Devils",
                "links": {
                  "web": {
                    "teams": {
                      "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils"
                    }
                  },
                  "mobile": {
                    "teams": {
                      "href": "https://www.espn.com/mens-college-basketball/team/_/id/150/duke-blue-devils"
                    }
                  }
                }
              }
            }
          ],
          "premium": false,
          "links": {
            "web": {
              "href": "https://www.espn.com/espn/feature/story/_/page/bracketology/ncaa-bracketology-2025-march-madness-men-field-predictions"
            },
            "mobile": {
              "href": "http://m.espn.go.com/wireless/story?storyId=30302581"
            },
            "api": {
              "self": {
                "href": "https://content.core.api.espn.com/v1/sports/news/30302581"
              }
            },
            "app": {
              "sportscenter": {
                "href": "sportscenter://x-callback-url/showStory?uid=30302581"
              }
            }
          },
          "byline": "Joe Lunardi"
        }
      ]
    }
    ```

**See also:** [Team Data](#team-data)

### Conferences (Groups) Endpoint {#conferences}
- URL: `/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard/conferences`
- Retrieves conference information
- Example curl:
```bash
curl "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard/conferences"
```

??? example "Example Response (real data, truncated)"
    ```json
    {
      "conferences": [
        {
          "id": "2",
          "name": "Atlantic Coast Conference",
          "shortName": "ACC",
          "groupId": "1",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/acc.png",
          "teams": []
        },
        {
          "id": "4",
          "name": "Big Ten Conference",
          "shortName": "Big Ten",
          "groupId": "5",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/b1g.png",
          "teams": []
        },
        {
          "id": "8",
          "name": "Big 12 Conference",
          "shortName": "Big 12",
          "groupId": "4",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/b12.png",
          "teams": []
        },
        {
          "id": "5",
          "name": "Big East Conference",
          "shortName": "Big East",
          "groupId": "3",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/bigeast.png",
          "teams": []
        },
        {
          "id": "21",
          "name": "Pac-12 Conference",
          "shortName": "Pac-12",
          "groupId": "9",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/pac12.png",
          "teams": []
        },
        {
          "id": "23",
          "name": "Southeastern Conference",
          "shortName": "SEC",
          "groupId": "8",
          "logo": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/sec.png",
          "teams": []
        }
      ]
    }
    ```

## API Limitations and Considerations {#limitations}

1. **No official documentation**: ESPN does not officially document these APIs
2. **Rate limiting**: Excessive requests may lead to temporary blocking
3. **Inconsistent structures**: Response structures can vary across endpoints and seasons
4. **Tournament bracket endpoints**: Historical tournament bracket data may use different endpoints
5. **Base URL variations**: Some endpoints use v2 API path, others use v3

!!! warning "API Stability"
    Since these are undocumented APIs, they may change without notice. Always include error handling in your code.

## Testing the APIs {#testing}

To test these APIs effectively:

1. **Rate Limiting**: Space out requests to avoid being blocked (1-2 seconds between requests)
2. **Postman Collection**: Consider creating a Postman collection for easy testing
3. **Error Handling**: Always implement error handling in your code
4. **User Agent**: Use a reasonable User-Agent header to identify your application

## Critical Parameters for Data Completeness {#critical-parameters}

1. **Scoreboard Endpoint**:
   - **`groups=50`**: CRITICAL parameter to get all Division I games
   - **`limit=200+`**: Needed during busy days with many games
   - Without these parameters, you'll only get Top 25 or featured games

2. **Teams Endpoint**:
   - Must iterate through multiple pages (page=1, page=2, etc.)
   - Each page returns 50 teams, but there are 350+ Division I teams

3. **Players (Athletes) Endpoint**:
   - Use `limit=10000` to get all 8000+ athletes in one request
   - Otherwise, must paginate through 300+ pages with default limit of 25

4. **Statistics Endpoint**:
   - Contains ~570 teams
   - Default pagination of 25 teams per page requires iterating through 23 pages
