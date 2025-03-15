#!/usr/bin/env python
"""
NCAA Basketball Data Collection Pipeline

This script runs the entire data collection and validation pipeline for NCAA basketball data.
It collects data from the ESPN API, processes it, and validates the results.
"""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories for data collection."""
    directories = [
        "data/seasons",
        "data/validated",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


def run_command(command, description):
    """Run a shell command and log the output."""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        logger.info(f"Command completed successfully: {description}")
        logger.debug(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {description}")
        logger.error(f"Error: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error output: {e.stderr}")
        return False


def main():
    """Main function to run the data collection pipeline."""
    parser = argparse.ArgumentParser(description="NCAA Basketball Data Collection Pipeline")
    parser.add_argument(
        "--start-year",
        type=int,
        default=2023,
        help="Start year for data collection (default: 2023)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2023,
        help="End year for data collection (default: 2023)"
    )
    parser.add_argument(
        "--skip-collection",
        action="store_true",
        help="Skip the data collection step and only run validation"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip the validation step and only run collection"
    )
    
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Record start time
    start_time = datetime.now()
    logger.info(f"Starting data collection pipeline at {start_time}")
    logger.info(f"Collecting data for years: {args.start_year} to {args.end_year}")
    
    # Step 1: Collect data
    if not args.skip_collection:
        collection_command = (
            f"python src/data/collect_ncaa_data.py "
            f"--start-year {args.start_year} "
            f"--end-year {args.end_year}"
        )
        
        if not run_command(collection_command, "Data collection"):
            logger.error("Data collection failed. Exiting pipeline.")
            return 1
    else:
        logger.info("Skipping data collection step as requested.")
    
    # Step 2: Validate data
    if not args.skip_validation:
        validation_command = "python src/data/validate_ncaa_data.py"
        
        if not run_command(validation_command, "Data validation"):
            logger.error("Data validation failed. Exiting pipeline.")
            return 1
    else:
        logger.info("Skipping data validation step as requested.")
    
    # Record end time and calculate duration
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info(f"Data collection pipeline completed at {end_time}")
    logger.info(f"Total duration: {duration}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 