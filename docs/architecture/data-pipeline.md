---
title: Data Pipeline
description: Overview of the data pipeline for the NCAA Basketball Prediction Model
---

# Data Pipeline

This document describes the data pipeline for the NCAA Basketball Prediction Model, focusing on the MVP implementation.

## Overview

The data pipeline follows the medallion architecture pattern with three sequential processing layers:

```mermaid
flowchart LR
    E[ESPN APIs] -->|Extract| B[Bronze Layer]
    B -->|Transform| S[Silver Layer]
    S -->|Feature Engineering| G[Gold Layer]
    G -->|Train| M[ML Models]

    style B fill:#cd7f32,color:white
    style S fill:#c0c0c0,color:black
    style G fill:#ffd700,color:black
    style M fill:#90ee90,color:black
```

## Data Sources

The project uses ESPN's undocumented APIs to retrieve NCAA basketball data:

### Primary Endpoints (MVP)

- **Scoreboard API**: Game schedules, scores, and basic game information
  - URL: `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`
  - Parameters: `dates`, `groups` (conferences), `limit`

- **Teams API**: Team information and metadata
  - URL: `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team_id}`

### Request Implementation

```python
def fetch_scoreboard(date: str, limit: int = 100) -> dict:
    """
    Fetch scoreboard data for a specific date.
    
    Args:
        date: Date in YYYYMMDD format
        limit: Maximum number of games to return
        
    Returns:
        JSON response as dictionary
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    params = {
        "dates": date,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()
```

## Bronze Layer

The Bronze layer preserves raw data from ESPN APIs in its original form.

### Implementation

1. **Storage Format**: DuckDB tables with `bronze_{api_endpoint_name}` naming convention
2. **Data Preservation**: Original JSON stored in a `raw_data` column along with metadata
3. **Schema Design**:
   ```
   CREATE TABLE bronze_scoreboard (
       id INTEGER PRIMARY KEY,
       date STRING,
       ingestion_timestamp TIMESTAMP,
       source_type STRING,
       content_hash STRING,
       raw_data STRING
   )
   ```
4. **Storage Location**: All data stored in a single DuckDB database file in the `data` directory
5. **Metadata Tracking**: Additional columns for request parameters, hash values, and lineage tracking

## Silver Layer

The Silver layer transforms raw data into cleaned, normalized structures.

### Core Entities

- **Teams**: Team information and metadata
- **Games**: Game schedules, scores, and outcomes
- **Seasons**: Season definitions and timeframes
- **Conferences**: Conference groupings and membership

### Implementation

1. **Storage Format**: DuckDB tables with `silver_{entity_name}` naming convention
2. **Same Database**: Silver tables stored in the same DuckDB database as Bronze layer
3. **Transformation Process**:
   - Parse JSON data from bronze layer tables
   - Apply data type conversions
   - Normalize nested structures
   - Implement data validation
   - Create relationships between entities
4. **Data Lineage**: Track source records from bronze layer to maintain data provenance

### Example Transformation

```python
def process_games(raw_data: dict) -> List[dict]:
    """
    Process raw scoreboard data into normalized game records.
    
    Args:
        raw_data: Raw JSON data from scoreboard API
        
    Returns:
        List of normalized game dictionaries
    """
    games = []
    
    for event in raw_data.get("events", []):
        game_id = event.get("id")
        competitions = event.get("competitions", [])
        
        if not competitions:
            continue
            
        competition = competitions[0]
        
        # Extract teams and scores
        teams_data = {}
        for competitor in competition.get("competitors", []):
            is_home = competitor.get("homeAway") == "home"
            team_id = competitor.get("team", {}).get("id")
            score = competitor.get("score")
            
            role = "home" if is_home else "away"
            teams_data[role] = {
                "team_id": team_id,
                "score": int(score) if score else None
            }
        
        # Create normalized game record
        game = {
            "game_id": game_id,
            "date": event.get("date"),
            "status": competition.get("status", {}).get("type", {}).get("name"),
            "home_team_id": teams_data.get("home", {}).get("team_id"),
            "away_team_id": teams_data.get("away", {}).get("team_id"),
            "home_score": teams_data.get("home", {}).get("score"),
            "away_score": teams_data.get("away", {}).get("score"),
            "neutral_site": competition.get("neutralSite", False),
            "conference_game": competition.get("conferenceCompetition", False)
        }
        
        games.append(game)
    
    return games
```

## Gold Layer

The Gold layer generates features for machine learning models.

### MVP Features

1. **Team Performance**:
   - Win/loss record (overall, home/away, conference)
   - Scoring averages (points for/against)
   - Recent performance (last 5/10 games)

2. **Game Context**:
   - Home/away/neutral
   - Days of rest
   - Conference matchup
   - Historical matchup results

### Implementation

```python
def calculate_team_features(team_id: str, games: List[dict]) -> dict:
    """
    Calculate team performance features from game data.
    
    Args:
        team_id: Team identifier
        games: List of processed game dictionaries
        
    Returns:
        Dictionary of team features
    """
    team_games = [g for g in games if g["home_team_id"] == team_id or g["away_team_id"] == team_id]
    
    # Calculate overall record
    wins = 0
    losses = 0
    points_for = 0
    points_against = 0
    
    for game in team_games:
        is_home = game["home_team_id"] == team_id
        team_score = game["home_score"] if is_home else game["away_score"]
        opponent_score = game["away_score"] if is_home else game["home_score"]
        
        if team_score > opponent_score:
            wins += 1
        elif team_score < opponent_score:
            losses += 1
            
        points_for += team_score if team_score else 0
        points_against += opponent_score if opponent_score else 0
    
    # Calculate averages
    games_played = wins + losses
    if games_played > 0:
        avg_points_for = points_for / games_played
        avg_points_against = points_against / games_played
        win_pct = wins / games_played
    else:
        avg_points_for = 0
        avg_points_against = 0
        win_pct = 0
    
    return {
        "team_id": team_id,
        "games_played": games_played,
        "wins": wins,
        "losses": losses,
        "win_pct": win_pct,
        "avg_points_for": avg_points_for,
        "avg_points_against": avg_points_against
    }
```

## Data Flow Execution

The data pipeline is executed through a command-line interface with the following steps:

1. **Ingest**: Fetch and store raw data
   ```bash
   python run.py ingest scoreboard --date 2023-03-01
   ```

2. **Process**: Transform raw data into silver layer
   ```bash
   python run.py process bronze-to-silver --entity games
   ```

3. **Features**: Generate gold layer features
   ```bash
   python run.py features generate --feature-set team_performance
   ```

4. **Model**: Train and evaluate prediction models
   ```bash
   python run.py model train --model-type logistic --feature-set team_performance
   ```

## Future Enhancements

In later phases, the data pipeline will be expanded to include:

1. Additional data sources (player statistics, advanced metrics)
2. More sophisticated feature engineering
3. Automated data quality monitoring
4. Incremental processing capabilities
5. Historical data backfilling
