"""Database utilities for the NCAA Basketball Prediction Model.

This module provides DuckDB integration for storing and retrieving NCAA basketball data,
including bronze, silver, and gold layer tables following the medallion architecture.
It offers a unified interface for managing database connections and operations.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb
import structlog

# Initialize logger
logger = structlog.get_logger(__name__)


class Database:
    """Database utility class for DuckDB operations."""

    def __init__(self: "Database", db_path: str, create_if_missing: bool = True) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to DuckDB database file
            create_if_missing: Create database if it doesn't exist
        """
        self.db_path = Path(db_path)

        # Ensure parent directory exists
        if create_if_missing:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Log connection details
        logger.debug("Connecting to database", path=str(self.db_path))

        # Connect to database
        self.conn = duckdb.connect(str(self.db_path))

        # Initialize tables if necessary
        self._initialize_tables()

    def _initialize_tables(self: "Database") -> None:
        """Initialize database tables if they don't exist."""
        # Bronze layer table for scoreboard data
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bronze_scoreboard (
                id INTEGER,
                date VARCHAR,
                source_url VARCHAR,
                parameters VARCHAR,
                content_hash VARCHAR,
                raw_data VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Check if index exists before creating it
        index_exists = self.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_bronze_scoreboard_date'
        """,
        ).fetchone()

        if not index_exists:
            # Create index on date for faster lookups
            self.conn.execute(
                """
                CREATE INDEX idx_bronze_scoreboard_date ON bronze_scoreboard(date)
            """,
            )

    def insert_bronze_scoreboard(
        self: "Database",
        date: str,
        url: str,
        params: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        """Insert scoreboard data into the bronze layer.

        Args:
            date: Date string in YYYY-MM-DD format
            url: Source URL
            params: Request parameters
            data: Response data
        """
        # Check if data already exists for this date and URL
        existing = self.conn.execute(
            """
            SELECT id FROM bronze_scoreboard
            WHERE date = ? AND source_url = ?
        """,
            [date, url],
        ).fetchone()

        if existing:
            logger.info("Duplicate scoreboard data found, skipping", date=date, url=url)
            return

        # Get next ID
        max_id_result = self.conn.execute("SELECT MAX(id) FROM bronze_scoreboard").fetchone()
        # Handle case where table is empty
        max_id = 0 if max_id_result[0] is None else max_id_result[0]
        record_id = max_id + 1

        # Prepare data
        params_json = json.dumps(params)
        json_data = json.dumps(data)
        content_hash = hashlib.sha256(json_data.encode("utf-8")).hexdigest()

        # Insert data
        self.conn.execute(
            """
            INSERT INTO bronze_scoreboard (id, date, source_url, parameters, content_hash, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            [record_id, date, url, params_json, content_hash, json_data],
        )

        logger.info("Inserted scoreboard data", date=date, url=url)

    def get_processed_dates(self: "Database", source: str = "bronze_scoreboard") -> list[str]:
        """Get list of dates that have already been processed.

        Returns:
            List of dates in YYYY-MM-DD format
        """
        if source != "bronze_scoreboard":
            return []

        result = self.conn.execute(
            """
            SELECT DISTINCT date FROM bronze_scoreboard
        """,
        ).fetchall()

        return [r[0] for r in result]

    def close(self: "Database") -> None:
        """Close database connection."""
        self.conn.close()
        logger.debug("Database connection closed")

    def __enter__(self: "Database") -> "Database":
        """Enter context manager."""
        return self

    def __exit__(
        self: "Database",
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit context manager."""
        self.close()
