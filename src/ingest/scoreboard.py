import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import structlog

from utils.config import ESPNApiConfig
from utils.database import Database
from utils.date_utils import (
    format_date_for_espn, 
    generate_date_range, 
    get_season_date_range,
    get_today,
    get_yesterday
)
from utils.espn_api_client import ESPNApiClient

# Initialize logger
logger = structlog.get_logger(__name__)

class ScoreboardIngestion:
    """Scoreboard data ingestion from ESPN API."""
    
    def __init__(self, espn_api_config: ESPNApiConfig, db_path: str = "data/ncaa_basketball.duckdb"):
        """
        Initialize scoreboard ingestion.
        
        Args:
            espn_api_config: ESPN API configuration
            db_path: Path to DuckDB database
        """
        self.api_client = ESPNApiClient(
            base_url=espn_api_config.base_url,
            endpoints=espn_api_config.endpoints,
            request_delay=espn_api_config.request_delay,
            max_retries=espn_api_config.max_retries,
            timeout=espn_api_config.timeout
        )
        self.db_path = db_path
        self.batch_size = espn_api_config.batch_size
        
        logger.debug("Initialized scoreboard ingestion", 
                    db_path=db_path, 
                    batch_size=self.batch_size)
    
    async def fetch_and_store_date(self, date: str, db: Database) -> None:
        """
        Fetch and store scoreboard data for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            db: Database connection
        """
        # Convert date to ESPN format
        espn_date = format_date_for_espn(date)
        
        try:
            # Fetch data from ESPN API
            data = await self.api_client.fetch_scoreboard(espn_date)
            
            # Store data in bronze layer
            url = self.api_client._build_url("scoreboard")
            params = {
                "dates": espn_date,
                "groups": "50",
                "limit": 200
            }
            
            # Insert into database
            db.insert_bronze_scoreboard(date, url, params, data)
            
            logger.info("Successfully processed date", date=date)
            
        except Exception as e:
            logger.error("Failed to process date", date=date, error=str(e))
            raise
    
    async def process_date_range(self, dates: List[str]) -> None:
        """
        Process a range of dates in batches.
        
        Args:
            dates: List of dates in YYYY-MM-DD format
        """
        logger.info("Processing date range", 
                   start=dates[0], 
                   end=dates[-1], 
                   total_dates=len(dates))
        
        # Get already processed dates
        with Database(self.db_path) as db:
            processed_dates = set(db.get_processed_dates())
        
        # Filter out already processed dates
        dates_to_process = [d for d in dates if d not in processed_dates]
        
        if not dates_to_process:
            logger.info("All dates already processed", total_dates=len(dates))
            return
        
        logger.info("Dates to process", 
                   count=len(dates_to_process), 
                   total_dates=len(dates),
                   already_processed=len(dates) - len(dates_to_process))
        
        # Process in batches
        for i in range(0, len(dates_to_process), self.batch_size):
            batch = dates_to_process[i:i + self.batch_size]
            logger.info("Processing batch", 
                       batch_start=batch[0], 
                       batch_end=batch[-1],
                       batch_size=len(batch))
            
            with Database(self.db_path) as db:
                # Process each date in the batch
                tasks = [self.fetch_and_store_date(date, db) for date in batch]
                await asyncio.gather(*tasks)
            
            logger.info("Completed batch", 
                       batch_start=batch[0], 
                       batch_end=batch[-1])

def ingest_scoreboard(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    yesterday: bool = False,
    today: bool = False,
    seasons: Optional[List[str]] = None,
    year: Optional[int] = None,
    espn_api_config: ESPNApiConfig = None,
    db_path: str = "data/ncaa_basketball.duckdb"
) -> None:
    """
    Ingest scoreboard data from ESPN API.
    
    Args:
        date: Single date to ingest (YYYY-MM-DD)
        start_date: Start date for range (YYYY-MM-DD)
        end_date: End date for range (YYYY-MM-DD)
        yesterday: Ingest data for yesterday
        today: Ingest data for today
        seasons: List of seasons in YYYY-YY format
        year: Calendar year to ingest
        espn_api_config: ESPN API configuration
        db_path: Path to DuckDB database
    """
    # Initialize dates list
    dates_to_process = []
    
    # Handle single date
    if date:
        dates_to_process = [date]
    
    # Handle yesterday flag
    elif yesterday:
        dates_to_process = [get_yesterday()]
    
    # Handle today flag
    elif today:
        dates_to_process = [get_today()]
    
    # Handle year
    elif year:
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        dates_to_process = generate_date_range(start, end)
    
    # Handle date range
    elif start_date and end_date:
        dates_to_process = generate_date_range(start_date, end_date)
    
    # Handle seasons
    elif seasons:
        for season in seasons:
            season_start, season_end = get_season_date_range(season)
            season_dates = generate_date_range(season_start, season_end)
            dates_to_process.extend(season_dates)
    
    # Default to historical start through yesterday if nothing specified
    elif espn_api_config.historical_start_date:
        hist_start = espn_api_config.historical_start_date
        yesterday = get_yesterday()
        dates_to_process = generate_date_range(hist_start, yesterday)
    
    # Ensure we have dates to process
    if not dates_to_process:
        logger.error("No dates specified for ingestion")
        raise ValueError("No dates specified for ingestion")
    
    # Sort dates and remove duplicates
    dates_to_process = sorted(list(set(dates_to_process)))
    
    # Create ingestion instance
    ingestion = ScoreboardIngestion(espn_api_config, db_path)
    
    # Run the async process
    logger.info("Starting scoreboard ingestion", 
               date_count=len(dates_to_process),
               start_date=dates_to_process[0],
               end_date=dates_to_process[-1])
    
    asyncio.run(ingestion.process_date_range(dates_to_process))
    
    logger.info("Completed scoreboard ingestion", date_count=len(dates_to_process)) 