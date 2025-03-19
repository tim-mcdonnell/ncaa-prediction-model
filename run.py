#!/usr/bin/env python3
"""NCAA Basketball Prediction Model - Runner Script.

A simple entry point to run commands for the NCAA Basketball Prediction Model.
Run from the project root with: python run.py [command] [subcommand] [options]
"""

import sys
from pathlib import Path

import click
import structlog

# Add src directory to path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

from src.utils.config import get_config  # noqa: E402
from src.utils.logging import configure_logging  # noqa: E402

# Initialize logger
logger = structlog.get_logger(__name__)


@click.group()
@click.option("--log-level", default=None, help="Override logging level")
@click.option("--config-dir", default="config", help="Configuration directory")
@click.pass_context
def cli(ctx: click.Context, log_level: str | None, config_dir: str) -> None:
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
    configure_logging(
        log_level=log_level,
        json_logs=config.logging.json_format,
        log_file=config.logging.file,
    )

    # Store context for subcommands
    ctx.obj["log_level"] = log_level
    ctx.obj["config_dir"] = config_dir


# ======================================================================
# Ingest Commands
# ======================================================================


@cli.group()
def ingest() -> None:
    """Commands for data ingestion."""


@ingest.command()
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Date to fetch scoreboard data for (YYYY-MM-DD)",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for range (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for range (YYYY-MM-DD)",
)
@click.option("--yesterday", is_flag=True, help="Fetch data for yesterday")
@click.option("--today", is_flag=True, help="Fetch data for today")
@click.option("--seasons", help="Comma-separated list of seasons (YYYY-YY)")
@click.option("--year", type=int, help="Calendar year to fetch")
@click.pass_context
def scoreboard(ctx: click.Context, **kwargs: dict) -> None:
    """Ingest scoreboard data from ESPN API."""
    from src.ingest.scoreboard import ScoreboardIngestionConfig, ingest_scoreboard

    config = ctx.obj["config"]

    # Process date parameters
    if kwargs.get("date"):
        kwargs["date"] = kwargs["date"].strftime("%Y-%m-%d")
    if kwargs.get("start_date"):
        kwargs["start_date"] = kwargs["start_date"].strftime("%Y-%m-%d")
    if kwargs.get("end_date"):
        kwargs["end_date"] = kwargs["end_date"].strftime("%Y-%m-%d")

    # Process seasons if provided
    if kwargs.get("seasons"):
        kwargs["seasons"] = [s.strip() for s in kwargs["seasons"].split(",")]

    logger.info("Starting scoreboard ingestion", **kwargs)

    try:
        # Create ingestion config
        ingestion_config = ScoreboardIngestionConfig(
            espn_api_config=config.espn_api,
            db_path="data/ncaa.duckdb",
            **kwargs,
        )

        # Call the actual implementation
        ingest_scoreboard(ingestion_config)
        logger.info("Scoreboard ingestion completed successfully")
    except Exception as e:
        logger.exception("Scoreboard ingestion failed", error=str(e))
        sys.exit(1)


@ingest.command()
@click.option("--conference", help="Conference ID to limit ingestion")
@click.option("--seasons", help="Comma-separated list of seasons (YYYY-YY)")
@click.pass_context
def teams(ctx: click.Context, conference: str | None, seasons: str | None) -> None:
    """Ingest team data from ESPN API."""
    from src.ingest.teams import ingest_teams

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


@process.command()
@click.option("--entity", required=True, help="Entity to process")
@click.option("--incremental", is_flag=True, help="Only process new data")
def bronze_to_silver(entity: str, incremental: bool) -> None:
    """Process bronze data to silver layer."""
    logger.info("Processing bronze to silver", entity=entity, incremental=incremental)
    # Implementation here


# ======================================================================
# Features Commands
# ======================================================================


@cli.group()
def features() -> None:
    """Commands for feature engineering."""


@features.command()
@click.option("--feature-set", required=True, help="Feature set to generate")
def generate(feature_set: str) -> None:
    """Generate features for model training."""
    logger.info("Generating feature set", feature_set=feature_set)
    # Implementation here


@features.command("list")
@click.option("--entity", help="Filter features by entity")
def list_features(entity: str | None) -> None:
    """List available features."""
    logger.info("Listing features", entity=entity)
    # Implementation here


# ======================================================================
# Model Commands
# ======================================================================


@cli.group()
def model() -> None:
    """Commands for model operations."""


@model.command()
@click.option("--model-type", required=True, help="Type of model to train")
@click.option("--feature-set", required=True, help="Feature set to use for training")
def train(model_type: str, feature_set: str) -> None:
    """Train a prediction model."""
    logger.info("Training model", model_type=model_type, feature_set=feature_set)
    # Implementation here


@model.command()
@click.option("--model-id", required=True, help="ID of trained model to use")
@click.option("--upcoming", is_flag=True, help="Predict upcoming games")
@click.option("--date", type=click.DateTime(), help="Predict games for specific date")
def predict(model_id: str, upcoming: bool, date: click.DateTime | None) -> None:
    """Generate predictions using trained model."""
    date_str = date.strftime("%Y-%m-%d") if date else None
    logger.info(
        "Generating predictions",
        model_id=model_id,
        upcoming=upcoming,
        date=date_str,
    )
    # Implementation here


# ======================================================================
# Run the CLI
# ======================================================================

if __name__ == "__main__":
    cli()
