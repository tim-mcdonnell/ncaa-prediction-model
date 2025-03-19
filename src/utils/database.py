import duckdb
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import structlog
import hashlib

# Initialize logger
logger = structlog.get_logger(__name__)

class Database:
    """Database utility class for DuckDB operations."""
    
    def __init__(self, db_path: Union[str, Path], create_if_missing: bool = True):
        """
        Initialize database connection.
        
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
    
    def _initialize_tables(self) -> None:
        """Initialize database tables if they don't exist."""
        # Check if bronze_scoreboard table exists
        result = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bronze_scoreboard'
        """).fetchone()
        
        if not result:
            logger.info("Creating bronze_scoreboard table")
            self.conn.execute("""
                CREATE TABLE bronze_scoreboard (
                    id INTEGER PRIMARY KEY,
                    date STRING,
                    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_url STRING,
                    parameters STRING,
                    content_hash STRING,
                    raw_data STRING
                )
            """)
            
            # Create index on date for faster lookups
            self.conn.execute("""
                CREATE INDEX idx_bronze_scoreboard_date ON bronze_scoreboard(date)
            """)
    
    def insert_bronze_scoreboard(self, date: str, url: str, params: Dict[str, Any], 
                                data: Dict[str, Any]) -> None:
        """
        Insert scoreboard data into bronze_scoreboard table.
        
        Args:
            date: Date in YYYY-MM-DD format
            url: Request URL
            params: Request parameters
            data: Raw JSON response data
        """
        # Convert data to JSON string
        json_data = json.dumps(data)
        
        # Generate hash of data
        content_hash = hashlib.md5(json_data.encode()).hexdigest()
        
        # Convert params to JSON string
        params_json = json.dumps(params)
        
        # Check if record with same hash already exists
        existing = self.conn.execute("""
            SELECT id FROM bronze_scoreboard 
            WHERE date = ? AND content_hash = ?
        """, [date, content_hash]).fetchone()
        
        if existing:
            logger.info("Duplicate scoreboard data found, skipping", 
                       date=date, 
                       hash=content_hash)
            return
        
        # Insert data
        self.conn.execute("""
            INSERT INTO bronze_scoreboard (date, source_url, parameters, content_hash, raw_data)
            VALUES (?, ?, ?, ?, ?)
        """, [date, url, params_json, content_hash, json_data])
        
        logger.info("Inserted scoreboard data", date=date, hash=content_hash)
    
    def get_processed_dates(self) -> List[str]:
        """
        Get list of dates that have already been processed.
        
        Returns:
            List of dates in YYYY-MM-DD format
        """
        result = self.conn.execute("""
            SELECT DISTINCT date FROM bronze_scoreboard
        """).fetchall()
        
        return [r[0] for r in result]
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
        logger.debug("Database connection closed")
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager."""
        self.close() 