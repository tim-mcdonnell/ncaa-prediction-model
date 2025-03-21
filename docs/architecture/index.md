---
title: Project Architecture
description: Overview of the NCAA Basketball Prediction Model architecture
---

# NCAA Basketball Prediction Model Architecture

[TOC]

## System Overview

The NCAA Basketball Prediction Model follows a medallion architecture designed for data processing, feature engineering, and machine learning:

- **Bronze Layer**: Raw data preserved in partitioned Parquet files
- **Silver Layer**: Cleaned, transformed data in normalized structure in DuckDB
- **Gold Layer**: Feature-engineered datasets ready for modeling in DuckDB
- **ML Layer**: Models, predictions, and evaluation metrics

```mermaid
graph TD
    DS[ESPN API] -->|Extract| B[Bronze Layer<br>Raw Data<br>Parquet Files]
    B -->|Transform| S[Silver Layer<br>Processed Data<br>DuckDB]
    S -->|Feature Engineering| G[Gold Layer<br>Feature Sets<br>DuckDB]
    G -->|Train/Evaluate| ML[ML Models]
    ML -->|Generate| P[Predictions]

    style B fill:#cd7f32,color:white
    style S fill:#c0c0c0,color:black
    style G fill:#ffd700,color:black
    style ML fill:#b8e0d2,color:black
    style P fill:#87ceeb,color:black
```

## MVP Focus Areas

For the initial version, we're focusing on:

1. **Core ESPN Data Sources**:
   - Scoreboard data (games, scores, teams)
   - Team statistics
   - Basic player information

2. **Essential Features**:
   - Team performance metrics (win/loss records, scoring efficiency)
   - Game context (home/away, conference matchups)
   - Historical performance indicators

3. **Initial Prediction Models**:
   - Game outcome prediction (win/loss)
   - Basic evaluation framework

## Data Flow

The data flows through these processing stages:

1. **ESPN API → Bronze**: Raw data preserved in partitioned Parquet files
2. **Bronze → Silver**: Data cleaning, validation, and normalization in DuckDB
3. **Silver → Gold**: Feature engineering and preparation for modeling in DuckDB
4. **Gold → Models**: Training, evaluation, and prediction generation

## Implementation Technologies

- **Storage**: 
  - Bronze layer: Partitioned Parquet files with year-month partitioning
  - Silver and Gold layers: DuckDB for normalized and feature tables
- **Processing**: Python, Polars, SQL
- **Modeling**: Scikit-learn, PyTorch (later phases)

## Project Structure

```
ncaa-prediction-model/
├── config/              # Configuration files
├── data/                
│   ├── raw/             # Bronze layer - partitioned Parquet files
│   │   ├── scoreboard/  # Organized by API endpoint
│   │   │   ├── year=YYYY/ # Year partitions
│   │   │   │   └── month=MM/ # Month partitions
│   │   ├── teams/       # Teams endpoint data
│   │   └── ...          # Other endpoints
│   ├── ncaa.duckdb      # Database containing silver and gold layers
│   ├── predictions/     # Output predictions
│   └── models/          # Trained models
├── src/                 # Source code
│   ├── ingest/          # Data ingestion (Bronze)
│   ├── process/         # Data processing (Silver)
│   ├── features/        # Feature engineering (Gold)
│   ├── models/          # ML models
│   └── utils/           # Utilities
├── run.py               # Command-line interface
└── tests/               # Test suite
```

## Key Interfaces

1. **Data Ingestion**: ESPN API client for data collection
2. **Data Processing**: Transform functions for each entity type
3. **Feature Engineering**: Feature generation for model consumption
4. **Model Interface**: Training, evaluation, and prediction functions

## Development Phases

See [Development Phases](development-phases.md) for the project roadmap, which follows this progression:

1. **MVP**: Basic pipeline and initial prediction capability
2. **Phase 2**: Additional data sources and enhanced features
3. **Phase 3**: Advanced analytics and expanded model types

## Performance Benefits

The architecture provides significant performance advantages:

1. **Storage Efficiency**: Year-month partitioned Parquet reduces bronze layer storage by ~74% compared to DuckDB
2. **Optimized Reads**: Partition pruning improves query performance for time-based queries
3. **Flexible Processing**: Decoupled storage enables parallel processing and better workload management

## Related Documentation

- [Data Pipeline](data-pipeline.md): Data ingestion and processing details
- [Data Entities](data-entities.md): Entity structure and relationships
- [Data Directory Structure](data-directory-structure.md): Organization of data files
- [Configuration Management](configuration-management.md): Configuration approach
- [CLI Design](cli-design.md): Command-line interface design
- [Logging Strategy](logging-strategy.md): Logging approach
- [Development Phases](development-phases.md): Project roadmap
