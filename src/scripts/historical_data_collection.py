"""
Historical Data Collection Script

This script implements a comprehensive data collection process to gather,
validate, and store NCAA basketball data from 2000 to 2025 using the
implemented collection pipeline and data cleaning infrastructure.

The script handles:
- Collecting complete NCAA basketball data for specified seasons
- Validating all collected data for quality and completeness
- Storing data efficiently in Parquet format
- Generating comprehensive data quality reports
- Documenting any gaps or issues in historical data
- Creating data collection progress reports
- Handling API rate limits and failures gracefully
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import polars as pl

from src.data.cleaning.data_cleaner import CleaningRule, DataCleaner, QualityReport
from src.pipelines.collection_pipeline import CollectionPipeline, PipelineResult

# Configure logger
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "info") -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Log level (info, debug, warning, error)
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    
    level = level_map.get(log_level.lower(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class HistoricalDataCollector:
    """
    Manages the collection and processing of historical NCAA basketball data.
    
    This class orchestrates the collection of data across multiple seasons,
    cleaning and validation of the collected data, and storage of the results
    in appropriate formats.
    
    Attributes:
        start_year: First season year to collect
        end_year: Last season year to collect
        data_dir: Directory for storing collected data
        pipeline: Collection pipeline instance
        cleaner: Data cleaner instance
    """
    
    def __init__(
        self, 
        start_year: int = 2000, 
        end_year: int = 2025,
        data_dir: str = "data"
    ):
        """
        Initialize the historical data collector.
        
        Args:
            start_year: First season year to collect
            end_year: Last season year to collect
            data_dir: Directory for storing collected data
        """
        self.start_year = start_year
        self.end_year = end_year
        self.data_dir = data_dir
        
        # Initialize pipeline and cleaner
        self.pipeline = CollectionPipeline(data_dir=data_dir)
        self.cleaner = DataCleaner()
        
        logger.info(
            f"Initialized historical data collector for seasons {start_year}-{end_year}"
        )
    
    async def collect_seasons(self) -> List[PipelineResult]:
        """
        Collect data for all seasons in the configured range.
        
        Returns:
            List of pipeline results for each season
        """
        logger.info(f"Starting collection for seasons {self.start_year}-{self.end_year}")
        
        try:
            # Use the collection pipeline to collect all seasons
            results = await self.pipeline.collect_all_seasons(
                self.start_year, self.end_year
            )
            
            logger.info(f"Completed collection for {len(results)} seasons")
            return results
            
        except Exception as e:
            logger.exception(f"Error collecting seasons: {str(e)}")
            raise
    
    def clean_and_validate_data(
        self, data: Dict[str, pl.DataFrame]
    ) -> Tuple[pl.DataFrame, QualityReport]:
        """
        Clean and validate collected data.
        
        Args:
            data: Dictionary of collected data DataFrames
            
        Returns:
            Tuple of (cleaned data DataFrame, quality report)
        """
        logger.info("Cleaning and validating collected data")
        
        # For simplicity, we focus on games data, but this could be extended
        # to handle other data types
        games_df = data.get("games", pl.DataFrame())
        
        if games_df.is_empty():
            logger.warning("No games data found for cleaning and validation")
            return games_df, QualityReport(
                overall_stats={"total_rows": 0},
                column_stats=[]
            )
        
        # Apply common data fixes automatically
        # Define some basic cleaning rules
        cleaning_rules = [
            CleaningRule(
                column="jersey",
                rule_type="clip",
                params={"min_value": 0, "max_value": 99}
            ),
            CleaningRule(
                column="position",
                rule_type="fill_empty",
                params={"fill_value": "UNKNOWN"}
            )
        ]
        
        # Apply cleaning rules
        cleaned_data = self.cleaner.clean_data(games_df, cleaning_rules)
        
        # Apply additional common fixes
        cleaned_data = self.cleaner.fix_common_issues(cleaned_data)
        
        # Generate quality report
        quality_report = self.cleaner.generate_quality_report(cleaned_data)
        
        logger.info(
            f"Completed data cleaning and validation: "
            f"{quality_report.overall_stats.get('total_rows', 0)} rows, "
            f"{len(quality_report.data_issues)} issues identified"
        )
        
        return cleaned_data, quality_report
    
    async def collect_and_process(self) -> List[Dict[str, Any]]:
        """
        Collect, clean, and validate data for all seasons.
        
        This method orchestrates the entire data collection and processing flow:
        1. Collect raw data for all seasons
        2. Clean and validate the data
        3. Store the cleaned data and quality reports
        
        Returns:
            List of dictionaries with results for each season
        """
        logger.info("Starting data collection and processing")
        
        # Collect raw data
        pipeline_results = await self.collect_seasons()
        
        # Process each season's data
        processed_results = []
        
        for i, result in enumerate(pipeline_results):
            season = self.start_year + i
            logger.info(f"Processing data for season {season}")
            
            # Skip failed collections
            if not result.status.value == "SUCCESS":
                logger.warning(f"Skipping failed collection for season {season}")
                processed_results.append({
                    "season": season,
                    "pipeline_result": result,
                    "error": str(result.error) if result.error else "Unknown error"
                })
                continue
            
            # Get the collected data
            output_data = result.output_data
            
            # Clean and validate the data
            cleaned_data, quality_report = self.clean_and_validate_data(output_data)
            
            # Store the cleaned data
            season_dir = Path(self.data_dir) / "cleaned" / str(season)
            season_dir.mkdir(parents=True, exist_ok=True)
            
            # Save cleaned games data
            if not cleaned_data.is_empty():
                games_path = season_dir / "games_cleaned.parquet"
                cleaned_data.write_parquet(games_path)
                logger.info(f"Saved cleaned data to {games_path}")
            
            # Save quality report
            report_path = season_dir / "quality_report.json"
            with open(report_path, "w") as f:
                json.dump(quality_report.model_dump(), f, indent=2)
            logger.info(f"Saved quality report to {report_path}")
            
            # Add to processed results
            processed_results.append({
                "season": season,
                "pipeline_result": result,
                "cleaned_data": cleaned_data,
                "quality_report": quality_report
            })
        
        logger.info(f"Completed processing for {len(processed_results)} seasons")
        return processed_results


def create_progress_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a progress report based on collection results.
    
    Args:
        results: List of processing results for each season
        
    Returns:
        Progress report dictionary
    """
    total_games = 0
    total_teams = 0
    total_issues = 0
    
    seasons_data = []
    
    for result in results:
        season = result.get("season")
        pipeline_result = result.get("pipeline_result")
        quality_report = result.get("quality_report")
        
        # Skip entries without proper data
        if not pipeline_result or not hasattr(pipeline_result, "metadata"):
            continue
        
        # Get metadata from pipeline result
        metadata = pipeline_result.metadata or {}
        games_count = metadata.get("games_count", 0)
        teams_count = metadata.get("teams_count", 0)
        
        # Get quality information
        issues = []
        if quality_report:
            issues = quality_report.data_issues
            
        # Update totals
        total_games += games_count
        total_teams += teams_count
        total_issues += len(issues)
        
        # Add season data
        seasons_data.append({
            "year": season,
            "games_count": games_count,
            "teams_count": teams_count,
            "data_issues": issues,
            "status": pipeline_result.status.value
        })
    
    # Create the final report
    report = {
        "timestamp": datetime.now().isoformat(),
        "seasons": seasons_data,
        "total_games": total_games,
        "total_teams": total_teams,
        "total_seasons": len(seasons_data),
        "total_issues": total_issues
    }
    
    return report


async def collect_historical_data(
    start_year: int = 2000,
    end_year: int = 2025,
    data_dir: str = "data",
    log_level: str = "info"
) -> None:
    """
    Main function to collect and process historical NCAA basketball data.
    
    Args:
        start_year: First season year to collect
        end_year: Last season year to collect
        data_dir: Directory for storing collected data
        log_level: Logging level
    """
    # Setup logging
    setup_logging(log_level)
    
    logger.info(
        f"Starting historical data collection for seasons {start_year}-{end_year}"
    )
    
    try:
        # Create collector
        collector = HistoricalDataCollector(
            start_year=start_year,
            end_year=end_year,
            data_dir=data_dir
        )
        
        # Collect and process data
        results = await collector.collect_and_process()
        
        # Create progress report
        report = create_progress_report(results)
        
        # Save progress report
        reports_dir = Path(data_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = reports_dir / f"collection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2))
        
        logger.info(f"Collection completed. Progress report saved to {report_path}")
        
        # Print summary
        print("\nCollection Summary:")
        print(f"Seasons processed: {report.get('total_seasons', 0)}")
        print(f"Total games collected: {report.get('total_games', 0)}")
        print(f"Total teams collected: {report.get('total_teams', 0)}")
        print(f"Data issues identified: {report.get('total_issues', 0)}")
        print(f"Report saved to: {report_path}")
        
    except Exception as e:
        logger.exception(f"Error in historical data collection: {str(e)}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect historical NCAA basketball data"
    )
    parser.add_argument(
        "--start-year", 
        type=int, 
        default=2000,
        help="First season year to collect"
    )
    parser.add_argument(
        "--end-year", 
        type=int, 
        default=2025,
        help="Last season year to collect"
    )
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default="data",
        help="Directory for storing collected data"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Run the collection
    asyncio.run(collect_historical_data(
        start_year=args.start_year,
        end_year=args.end_year,
        data_dir=args.data_dir,
        log_level=args.log_level
    )) 