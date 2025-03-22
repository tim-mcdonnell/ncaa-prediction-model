"""Data ingestion package for NCAA basketball data.

This package contains modules for ingesting data from various sources
into the bronze layer of the medallion architecture.
"""

from .base import BaseIngestion, BaseIngestionConfig
from .ingest_all import (
    UnifiedIngestionConfig,
    ingest_all,
    ingest_multiple_endpoints,
)
from .scoreboard import (
    ScoreboardIngestion,
    ScoreboardIngestionConfig,
    ingest_scoreboard,
)
from .teams import (
    TeamsIngestion,
    TeamsIngestionConfig,
    ingest_teams,
)

__all__ = [
    "BaseIngestion",
    "BaseIngestionConfig",
    "ingest_all",
    "ingest_multiple_endpoints",
    "ingest_scoreboard",
    "ingest_teams",
    "ScoreboardIngestion",
    "ScoreboardIngestionConfig",
    "TeamsIngestion",
    "TeamsIngestionConfig",
    "ingest_teams",
    # Unified ingestion
    "UnifiedIngestionConfig",
    "ingest_all",
    "ingest_multiple_endpoints",
]
