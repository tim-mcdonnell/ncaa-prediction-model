---
title: Data Directory Structure
description: Organization of the NCAA Basketball Analytics project data directory with partitioned Parquet for bronze layer and DuckDB for silver/gold layers
---

# Data Directory Structure

[TOC]

## Overview

This document outlines the organization of the data directory in the NCAA Basketball Analytics project. The approach uses partitioned Parquet files for the bronze layer and DuckDB for silver and gold layers, maintaining medallion architecture principles with optimized storage efficiency.

```mermaid
flowchart TD
    D[/data/] --> R[/raw/]
    D --> DB[(ncaa.duckdb)]
    D --> P[/predictions/]
    D --> MD[/models/]

    R --> E1[/{endpoint1}/]
    R --> E2[/{endpoint2}/]
    R --> EN[/...other endpoints/]

    E1 --> YP1[/year=YYYY/]
    E1 --> YP2[/year=YYYY/]
    YP1 --> MP1[/month=MM/]
    YP1 --> MP2[/month=MM/]
    
    DB --> S[Silver Layer Tables]
    DB --> G[Gold Layer Tables]
    DB --> MT[Metadata Tables]

    style R fill:#cd7f32,color:white
    style S fill:#c0c0c0,color:black
    style G fill:#ffd700,color:black
    style MT fill:#8a2be2,color:white
```

## Directory Structure

```
ncaa-prediction-model/
└── data/
    ├── raw/                              # Bronze layer data stored as partitioned Parquet files
    │   ├── scoreboard/                   # Organized by API endpoint
    │   │   ├── year=YYYY/                # Year partitions
    │   │   │   └── month=MM/             # Month partitions
    │   │   │       └── *.parquet         # Parquet files with raw data
    │   ├── teams/                        # Teams API endpoint
    │   │   └── ...
    │   └── ...                           # Other API endpoints
    │
    ├── ncaa.duckdb                       # DuckDB database containing silver and gold layers
    │
    ├── predictions/                      # Output prediction files
    │   └── YYYY-MM-DD/                   # Organized by prediction date
    │
    └── models/                           # Trained ML models
        └── model_name/                   # Organized by model type
            └── version/                  # Version-controlled model files
```

## Key Components

### 1. Bronze Layer (Raw Data)

The bronze layer preserves raw API data in partitioned Parquet files:

- **Directory Structure**: Files organized in `data/raw/{endpoint}/year=YYYY/month=MM/` pattern
- **Parquet Format**: Efficient columnar storage with ZSTD compression
- **Data Preservation**: Original JSON stored in a `raw_data` column
- **Metadata Columns**: Each file includes date, ingestion timestamps, content hashes, and source information
- **Partitioning Benefits**: Year-month partitioning provides optimal compression (around 4x better than single file)
- **Incremental Updates**: New data is appended to appropriate partition directories

Example schema for bronze layer Parquet files:

```python
schema = {
    "id": Int32,                # Record identifier
    "date": String,             # Date in YYYY-MM-DD format
    "source_url": String,       # API endpoint URL
    "parameters": String,       # Query parameters as JSON string
    "content_hash": String,     # Content hash for change detection
    "raw_data": String,         # Original JSON response
    "created_at": Timestamp,    # Ingestion timestamp
    "year": String,             # Partition value (redundant but useful)
    "month": String             # Partition value (redundant but useful)
}
```

### 2. Metadata Registry

The DuckDB database contains metadata tables for tracking data lineage:

#### Metadata Tables

- **source_metadata**: Information about raw data sources
  - Links source ID to raw data file paths
  - Tracks content hashes, ingestion timestamps, and processing status
- **silver_dependencies**: Lineage from bronze to silver
- **gold_dependencies**: Lineage from silver to gold
- **model_dependencies**: Lineage from gold to models
- **job_history**: Processing job execution history
- **change_detection**: Change tracking for incremental processing

### 3. Silver and Gold Layers

The DuckDB database contains normalized and feature-engineered tables:

#### Silver Layer Tables

Normalized entity tables derived from bronze data:

- **Table Naming**: Tables follow `silver_{entity_name}` pattern
- **seasons**: NCAA basketball seasons with dates and phases
- **teams**: Team information and metadata
- **players**: Player roster information
- **games**: Game events, results, and context
- **statistics**: Game and season statistics
- **venues**: Game locations
- **conferences**: Conference information
- **rankings**: Team rankings by poll

#### Gold Layer Tables

Feature-engineered tables derived from silver layer entities:

- **Table Naming**: Tables follow `gold_{feature_set_name}` pattern
- **team_performance**: Team level statistics, trends, and metrics
- **player_performance**: Player level statistics and metrics
- **game_context**: Game situation features (home/away, rest days, etc.)
- **historical_performance**: Historical matchups and outcomes
- **prediction_features**: Combined feature sets ready for model consumption

### 4. Predictions and Models

The remaining directories store prediction outputs and trained models:

- **predictions/**: Organized by prediction date
- **models/**: Organized by model type and version

## Storage Efficiency

The revised architecture provides significant advantages:

1. **Bronze Layer Efficiency**:
   - Year-month partitioning reduces storage requirements by approximately 74% compared to DuckDB storage
   - Optimized compression for similar data patterns within month partitions
   - Better parallel processing capabilities

2. **Silver/Gold Efficiency**:
   - DuckDB provides optimized columnar storage for processed data
   - SQL interface for complex analytics
   - Direct integration with analytics libraries

## Access Patterns

Common data access patterns with the new architecture:

### Accessing Bronze Layer Data

```python
def read_scoreboard_data(date):
    """Read scoreboard data for a specific date."""
    year, month, day = date.split("-")
    
    # Path to the specific partition
    path = f"data/raw/scoreboard/year={year}/month={month}/"
    
    # Read the partition with a filter
    df = pl.read_parquet(
        path, 
        filters=[pl.col("date") == date]
    )
    
    if len(df) > 0:
        # Get the raw data from the most recent record
        return df.sort("created_at", descending=True)[0, "raw_data"]
    else:
        return None
```

### Working with Silver Layer

```python
def get_team_games(team_id, season):
    """Get all games for a team in a season."""
    with duckdb.connect("data/ncaa.duckdb") as conn:
        return conn.execute("""
            SELECT * FROM silver_games
            WHERE (home_team_id = ? OR away_team_id = ?)
            AND season_id = ?
            ORDER BY game_date
        """, [team_id, team_id, season]).fetchdf()
```

## Data Pipeline Flow

The revised data pipeline follows this flow:

1. **Ingestion**:
   - Fetch data from ESPN APIs
   - Store in bronze layer Parquet files with appropriate metadata and partitioning
   - Update metadata registry

2. **Processing**:
   - Read bronze layer Parquet files 
   - Transform into silver layer normalized tables
   - Store in DuckDB
   - Update lineage tracking

3. **Feature Engineering**:
   - Create features from silver tables
   - Store as gold layer tables
   - Update feature dependencies

4. **Analysis & Prediction**:
   - Use gold layer tables for model training
   - Generate predictions
   - Store models and predictions in respective directories

## Backup Strategy

The recommended backup strategy:

1. **Bronze Layer**: Regular filesystem backups of Parquet files (incremental)
2. **DuckDB Database**:
   - Regular database dumps using DuckDB's export functionality
   - Consider WAL-based backup for more frequent recovery points
3. **Models & Predictions**: Version control or filesystem backups
