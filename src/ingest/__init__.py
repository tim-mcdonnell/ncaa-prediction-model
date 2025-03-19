"""
Data ingestion package for NCAA basketball data.

This package contains modules for ingesting data from various sources
into the bronze layer of the medallion architecture.
"""

from .scoreboard import ingest_scoreboard

__all__ = ["ingest_scoreboard"]
