#!/usr/bin/env python3
"""NCAA Basketball Prediction Model - Runner Script.

A simple entry point to run commands for the NCAA Basketball Prediction Model.
Run from the project root with: python run.py [command] [subcommand] [options]
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Add src directory to path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

from src.utils.config import get_config  # noqa: E402
from src.utils.logging import configure_logging  # noqa: E402

# Initialize logger
logger = structlog.get_logger(__name__)
console = Console()

# Create Typer app
app = typer.Typer(
    help="NCAA Basketball Prediction Model. "
    "Run commands for data ingestion, processing, model training, and more."
)

# Create sub-apps
ingest_app = typer.Typer(help="Commands for data ingestion.")
process_app = typer.Typer(help="Commands for data processing.")
features_app = typer.Typer(help="Commands for feature engineering.")
model_app = typer.Typer(help="Commands for model operations.")

# Add sub-apps to main app
app.add_typer(ingest_app, name="ingest")
app.add_typer(process_app, name="process")
app.add_typer(features_app, name="features")
app.add_typer(model_app, name="model")


# Global state
class State:
    config: Any = None
    log_level: str = "INFO"
    config_dir: str = "config"


state = State()


@app.callback()
def main(
    log_level: str | None = typer.Option(None, help="Override logging level"),
    config_dir: str = typer.Option("config", help="Configuration directory"),
):
    """NCAA Basketball Prediction Model.

    Run commands for data ingestion, processing, model training, and more.
    """
    # Load configuration
    config = get_config(Path(config_dir))
    state.config = config

    # Configure logging
    state.log_level = log_level or config.logging.level
    configure_logging(
        log_level=state.log_level,
        json_logs=config.logging.json_format,
        log_file=config.logging.file,
    )

    # Store context for subcommands
    state.config_dir = config_dir


# ======================================================================
# Ingest Commands
# ======================================================================

# Define options outside of function calls
DATE_OPTION = typer.Option(
    None, formats=["%Y-%m-%d"], help="Date to fetch scoreboard data for (YYYY-MM-DD)"
)
START_DATE_OPTION = typer.Option(
    None, formats=["%Y-%m-%d"], help="Start date for range (YYYY-MM-DD)"
)
END_DATE_OPTION = typer.Option(None, formats=["%Y-%m-%d"], help="End date for range (YYYY-MM-DD)")
YESTERDAY_OPTION = typer.Option(False, help="Fetch data for yesterday")
TODAY_OPTION = typer.Option(False, help="Fetch data for today")
SEASONS_OPTION = typer.Option(None, help="Comma-separated list of seasons (YYYY-YY)")
YEAR_OPTION = typer.Option(None, help="Calendar year to fetch")
CONCURRENCY_OPTION = typer.Option(
    None, help="Maximum number of concurrent requests (overrides configuration)"
)
AGGRESSIVE_OPTION = typer.Option(False, help="Use aggressive settings for maximum performance")
CAUTIOUS_OPTION = typer.Option(False, help="Use cautious settings for better reliability")
FORCE_UPDATE_OPTION = typer.Option(
    False, help="Force update of data even if it already exists (checks hash to detect changes)"
)

# Options for teams command
CONFERENCE_OPTION = typer.Option(None, help="Conference ID to limit ingestion")
TEAM_SEASONS_OPTION = typer.Option(None, help="Comma-separated list of seasons (YYYY-YY)")


@ingest_app.command("teams")
def teams(
    conference: str | None = CONFERENCE_OPTION,
    seasons: str | None = TEAM_SEASONS_OPTION,
):
    """Ingest team data from ESPN API."""
    from src.ingest.teams import ingest_teams

    # Process seasons if provided
    season_list = None
    if seasons:
        season_list = [s.strip() for s in seasons.split(",")]

    logger.info("Starting team ingestion", conference=conference, seasons=season_list)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Ingesting team data...", total=None)

            # Call the actual implementation
            ingest_teams(conference, season_list, state.config.espn_api)
            progress.update(task, completed=True)

        console.print("[bold green]Team ingestion completed successfully[/bold green]")
    except Exception as e:
        logger.exception("Team ingestion failed", error=str(e))
        console.print(f"[bold red]Team ingestion failed: {e!s}[/bold red]")
        sys.exit(1)


@ingest_app.command("scoreboard")
def scoreboard(
    date: datetime | None = DATE_OPTION,
    start_date: datetime | None = START_DATE_OPTION,
    end_date: datetime | None = END_DATE_OPTION,
    yesterday: bool = YESTERDAY_OPTION,
    today: bool = TODAY_OPTION,
    seasons: str | None = SEASONS_OPTION,
    year: int | None = YEAR_OPTION,
    concurrency: int | None = CONCURRENCY_OPTION,
    aggressive: bool = AGGRESSIVE_OPTION,
    cautious: bool = CAUTIOUS_OPTION,
    force_update: bool = FORCE_UPDATE_OPTION,
):
    """Ingest scoreboard data from ESPN API."""
    from src.ingest.scoreboard import ScoreboardIngestionConfig, ingest_scoreboard

    processed_kwargs: dict[str, Any] = {}

    # Process date parameters
    if date:
        processed_kwargs["date"] = date.strftime("%Y-%m-%d")

    if start_date:
        processed_kwargs["start_date"] = start_date.strftime("%Y-%m-%d")

    if end_date:
        processed_kwargs["end_date"] = end_date.strftime("%Y-%m-%d")

    # Copy other parameters
    for key, value in [
        ("yesterday", yesterday),
        ("today", today),
        ("year", year),
        ("concurrency", concurrency),
        ("aggressive", aggressive),
        ("cautious", cautious),
        ("force_update", force_update),
    ]:
        if value is not None:
            processed_kwargs[key] = value

    # Process seasons if provided
    if seasons:
        processed_kwargs["seasons"] = [s.strip() for s in seasons.split(",")]

    # Log concurrency settings if provided
    if concurrency:
        logger.info("Using custom concurrency setting", concurrency=concurrency)
    if aggressive:
        logger.info("Using aggressive performance settings")
    if cautious:
        logger.info("Using cautious reliability settings")
    if force_update:
        logger.info("Force update enabled - will re-fetch all requested dates")

    logger.info("Starting scoreboard ingestion", **processed_kwargs)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Ingesting scoreboard data...", total=None)

            # Create ingestion config
            ingestion_config = ScoreboardIngestionConfig(
                espn_api_config=state.config.espn_api,
                db_path="data/ncaa.duckdb",
                date=processed_kwargs.get("date"),
                start_date=processed_kwargs.get("start_date"),
                end_date=processed_kwargs.get("end_date"),
                yesterday=processed_kwargs.get("yesterday", False),
                today=processed_kwargs.get("today", False),
                seasons=processed_kwargs.get("seasons"),
                year=processed_kwargs.get("year"),
                concurrency=processed_kwargs.get("concurrency"),
                aggressive=processed_kwargs.get("aggressive", False),
                cautious=processed_kwargs.get("cautious", False),
                force_update=processed_kwargs.get("force_update", False),
            )

            # Call the actual implementation
            ingest_scoreboard(ingestion_config)
            progress.update(task, completed=True)

        console.print("[bold green]Scoreboard ingestion completed successfully[/bold green]")
    except Exception as e:
        logger.exception("Scoreboard ingestion failed", error=str(e))
        console.print(f"[bold red]Scoreboard ingestion failed: {e!s}[/bold red]")
        sys.exit(1)


# ======================================================================
# Process Commands
# ======================================================================

# Options for bronze_to_silver command
ENTITY_OPTION = typer.Option(..., help="Entity to process")
INCREMENTAL_OPTION = typer.Option(False, help="Only process new data")


@process_app.command("bronze-to-silver")
def bronze_to_silver(
    entity: str = ENTITY_OPTION,
    incremental: bool = INCREMENTAL_OPTION,
):
    """Process bronze data to silver layer."""
    logger.info("Processing bronze to silver", entity=entity, incremental=incremental)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Processing data...", total=None)
        # Implementation here
        progress.update(task, completed=True)

    console.print("[bold green]Processing completed successfully[/bold green]")


# ======================================================================
# Features Commands
# ======================================================================


@features_app.command("generate")
def generate_features(
    feature_set: str = typer.Option(..., help="Feature set to generate"),
):
    """Generate features for model training."""
    logger.info("Generating feature set", feature_set=feature_set)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Generating features...", total=None)
        # Implementation here
        progress.update(task, completed=True)

    console.print("[bold green]Feature generation completed successfully[/bold green]")


@features_app.command("list")
def list_features(
    entity: str | None = typer.Option(None, help="Filter features by entity"),
):
    """List available features."""
    logger.info("Listing features", entity=entity)

    # Implementation here
    console.print("[bold blue]Available Features:[/bold blue]")
    # Print features list here


# ======================================================================
# Model Commands
# ======================================================================

# Options for model commands
MODEL_TYPE_OPTION = typer.Option(..., help="Type of model to train")
FEATURE_SET_OPTION = typer.Option(..., help="Feature set to use for training")
MODEL_ID_OPTION = typer.Option(..., help="ID of trained model to use")
UPCOMING_OPTION = typer.Option(False, help="Predict upcoming games")
PREDICT_DATE_OPTION = typer.Option(
    None, formats=["%Y-%m-%d"], help="Predict games for specific date"
)


@model_app.command("train")
def train_model(
    model_type: str = MODEL_TYPE_OPTION,
    feature_set: str = FEATURE_SET_OPTION,
):
    """Train a prediction model."""
    logger.info("Training model", model_type=model_type, feature_set=feature_set)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Training model...", total=None)
        # Implementation here
        progress.update(task, completed=True)

    console.print("[bold green]Model training completed successfully[/bold green]")


@model_app.command("predict")
def predict(
    model_id: str = MODEL_ID_OPTION,
    upcoming: bool = UPCOMING_OPTION,
    date: datetime | None = PREDICT_DATE_OPTION,
):
    """Generate predictions using trained model."""
    date_str = date.strftime("%Y-%m-%d") if date else None
    logger.info(
        "Generating predictions",
        model_id=model_id,
        upcoming=upcoming,
        date=date_str,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Generating predictions...", total=None)
        # Implementation here
        progress.update(task, completed=True)

    console.print("[bold green]Predictions generated successfully[/bold green]")


# Options for migrate command
SOURCE_OPTION = typer.Option(
    "data/ncaa.duckdb", "--source", "-s", help="Source DuckDB database path"
)
DESTINATION_OPTION = typer.Option(
    "data/raw", "--destination", "-d", help="Destination directory for Parquet files"
)
BATCH_SIZE_OPTION = typer.Option(
    100, "--batch-size", "-b", help="Number of records to process in each batch"
)
ENDPOINT_OPTION = typer.Option(
    "all", "--endpoint", "-e", help="Endpoint to migrate (all, scoreboard, teams)"
)
VALIDATE_OPTION = typer.Option(True, "--validate/--no-validate", help="Validate migration results")


@app.command("migrate")
def migrate(
    source: str = SOURCE_OPTION,
    destination: str = DESTINATION_OPTION,
    batch_size: int = BATCH_SIZE_OPTION,
    endpoint: str = ENDPOINT_OPTION,
    validate: bool = VALIDATE_OPTION,
):
    """Migrate bronze layer data from DuckDB to partitioned Parquet files."""
    from src.ingest.migration import (
        migrate_bronze_layer,
        migrate_scoreboard_data,
        migrate_team_data,
        validate_migration,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        if endpoint == "all":
            task = progress.add_task("[green]Migrating all endpoints...", total=None)
            console.print("Migrating all endpoints from DuckDB to Parquet...")
            result = migrate_bronze_layer(
                db_path=source,
                output_dir=destination,
                batch_size=batch_size,
                validate=validate,
            )
            progress.update(task, completed=True)

            console.print("[bold green]Migration complete:[/bold green]")
            console.print(f"  Success: {result['success']}")

            for table_name, table_result in result.get("tables", {}).items():
                console.print(f"  [blue]{table_name.capitalize()}:[/blue]")
                console.print(f"    DuckDB records: {table_result.get('duckdb_count', 0)}")
                console.print(f"    Parquet records: {table_result.get('parquet_count', 0)}")

        elif endpoint == "scoreboard":
            task = progress.add_task("[green]Migrating scoreboard data...", total=None)
            console.print("Migrating scoreboard data from DuckDB to Parquet...")
            result = migrate_scoreboard_data(
                db_path=source,
                output_dir=destination,
                batch_size=batch_size,
                validate=validate,
            )
            progress.update(task, completed=True)

            console.print("[bold green]Migration complete:[/bold green]")
            console.print(f"  Success: {result['success']}")
            console.print(f"  Source records: {result.get('source_count', 0)}")
            console.print(f"  Migrated records: {result.get('migrated_count', 0)}")

        elif endpoint == "teams":
            task = progress.add_task("[green]Migrating team data...", total=None)
            console.print("Migrating team data from DuckDB to Parquet...")
            result = migrate_team_data(
                db_path=source,
                output_dir=destination,
                validate=validate,
            )
            progress.update(task, completed=True)

            console.print("[bold green]Migration complete:[/bold green]")
            console.print(f"  Success: {result['success']}")
            console.print(f"  Source records: {result.get('source_count', 0)}")
            console.print(f"  Migrated records: {result.get('migrated_count', 0)}")

        elif endpoint == "validate":
            task = progress.add_task("[green]Validating migration...", total=None)
            console.print("Validating migration from DuckDB to Parquet...")
            result = validate_migration(
                db_path=source,
                parquet_dir=destination,
            )
            progress.update(task, completed=True)

            console.print("[bold green]Validation complete:[/bold green]")
            console.print(f"  Success: {result['success']}")

            for table_name, table_result in result.get("tables", {}).items():
                console.print(f"  [blue]{table_name.capitalize()}:[/blue]")
                console.print(f"    DuckDB records: {table_result.get('duckdb_count', 0)}")
                console.print(f"    Parquet records: {table_result.get('parquet_count', 0)}")
                console.print(f"    Content match: {table_result.get('content_match', False)}")
        else:
            console.print(f"[bold red]Unknown endpoint: {endpoint}[/bold red]")
            console.print("Valid options: all, scoreboard, teams, validate")
            return 1

    return 0


# ======================================================================
# Run the CLI
# ======================================================================

if __name__ == "__main__":
    app()
