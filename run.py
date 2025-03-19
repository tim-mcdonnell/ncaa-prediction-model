#!/usr/bin/env python3
"""
NCAA Basketball Prediction Model - Runner Script.

A simple entry point to run commands for the NCAA Basketball Prediction Model.
Run from the project root with: python run.py [command] [subcommand] [options]
"""

import click
from pathlib import Path
import structlog
import sys
from typing import Optional

# Ensure src directory is in path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from utils.config import get_config
from utils.logging import configure_logging

# Initialize logger
logger = structlog.get_logger(__name__)

@click.group()
@click.option("--log-level", default=None, help="Override logging level")
@click.option("--config-dir", default="config", help="Configuration directory")
@click.pass_context
def cli(ctx: click.Context, log_level: Optional[str], config_dir: str) -> None:
    """NCAA Basketball Prediction Model.
    
    Run commands for data ingestion, processing, model training, and more.
    """
    # Initialize context object to share data between commands
    ctx.ensure_object(dict)
    
    # Load configuration
    config = get_config(Path(config_dir))
    ctx.obj["config"] = config
    
    # Configure logging
    log_level = log_level or config.logging.level
    configure_logging(log_level=log_level, 
                     json_logs=config.logging.json_format,
                     log_file=config.logging.file)
    
    # Store context for subcommands
    ctx.obj["log_level"] = log_level
    ctx.obj["config_dir"] = config_dir

# ======================================================================
# Ingest Commands
# ======================================================================

@cli.group()
def ingest() -> None:
    """Commands for data ingestion."""
    pass

@ingest.command()
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), 
             help="Date to fetch scoreboard data for (YYYY-MM-DD)")
@click.option("--seasons", help="Comma-separated list of seasons (YYYY-YY)")
@click.pass_context
def scoreboard(ctx: click.Context, date: Optional[click.DateTime], seasons: Optional[str]) -> None:
    """Ingest scoreboard data from ESPN API."""
    from ingest.scoreboard import ingest_scoreboard
    
    config = ctx.obj["config"]
    
    # Process date if provided
    date_str = date.strftime("%Y-%m-%d") if date else None
    
    # Process seasons if provided
    season_list = None
    if seasons:
        season_list = [s.strip() for s in seasons.split(",")]
    
    logger.info("Starting scoreboard ingestion", date=date_str, seasons=season_list)
    
    try:
        # Call the actual implementation
        ingest_scoreboard(date_str, season_list, config.espn_api)
        logger.info("Scoreboard ingestion completed successfully")
    except Exception as e:
        logger.exception("Scoreboard ingestion failed", error=str(e))
        sys.exit(1)

@ingest.command()
@click.option("--conference", help="Conference ID to limit ingestion")
@click.option("--seasons", help="Comma-separated list of seasons (YYYY-YY)")
@click.pass_context
def teams(ctx: click.Context, conference: Optional[str], seasons: Optional[str]) -> None:
    """Ingest team data from ESPN API."""
    from ingest.teams import ingest_teams
    
    config = ctx.obj["config"]
    
    # Process seasons if provided
    season_list = None
    if seasons:
        season_list = [s.strip() for s in seasons.split(",")]
    
    logger.info("Starting team ingestion", conference=conference, seasons=season_list)
    
    try:
        # Call the actual implementation
        ingest_teams(conference, season_list, config.espn_api)
        logger.info("Team ingestion completed successfully")
    except Exception as e:
        logger.exception("Team ingestion failed", error=str(e))
        sys.exit(1)

# ======================================================================
# Process Commands
# ======================================================================

@cli.group()
def process() -> None:
    """Commands for data processing."""
    pass

@process.command()
@click.option("--entity", required=True, help="Entity to process (teams, games, etc.)")
@click.option("--incremental", is_flag=True, help="Only process new data")
@click.pass_context
def bronze_to_silver(ctx: click.Context, entity: str, incremental: bool) -> None:
    """Process bronze data to silver layer."""
    logger.info("Processing bronze to silver", entity=entity, incremental=incremental)
    # Implementation would be added here

# ======================================================================
# Features Commands
# ======================================================================

@cli.group()
def features() -> None:
    """Commands for feature engineering."""
    pass

@features.command()
@click.option("--feature-set", required=True, help="Feature set to generate")
@click.pass_context
def generate(ctx: click.Context, feature_set: str) -> None:
    """Generate features for model training."""
    logger.info("Generating feature set", feature_set=feature_set)
    # Implementation would be added here

@features.command()
@click.option("--entity", help="Filter features by entity")
@click.pass_context
def list(ctx: click.Context, entity: Optional[str]) -> None:
    """List available features."""
    logger.info("Listing features", entity=entity)
    # Implementation would be added here

# ======================================================================
# Model Commands
# ======================================================================

@cli.group()
def model() -> None:
    """Commands for model operations."""
    pass

@model.command()
@click.option("--model-type", required=True, help="Type of model to train")
@click.option("--feature-set", required=True, help="Feature set to use for training")
@click.pass_context
def train(ctx: click.Context, model_type: str, feature_set: str) -> None:
    """Train a prediction model."""
    logger.info("Training model", model_type=model_type, feature_set=feature_set)
    # Implementation would be added here

@model.command()
@click.option("--model-id", required=True, help="Model ID to use for prediction")
@click.option("--upcoming", is_flag=True, help="Predict upcoming games")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), 
             help="Date to predict games for (YYYY-MM-DD)")
@click.pass_context
def predict(ctx: click.Context, model_id: str, upcoming: bool, 
           date: Optional[click.DateTime]) -> None:
    """Generate predictions using trained model."""
    date_str = date.strftime("%Y-%m-%d") if date else None
    logger.info("Generating predictions", model_id=model_id, 
               upcoming=upcoming, date=date_str)
    # Implementation would be added here

# ======================================================================
# Run the CLI
# ======================================================================

if __name__ == "__main__":
    cli() 