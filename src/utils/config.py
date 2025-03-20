"""Configuration utilities for the NCAA Basketball Prediction Model.

This module provides functionality for loading, validating, and accessing configuration
settings from YAML files. It includes support for configuring ESPN API access and
other system-wide settings.
"""

from dataclasses import dataclass
from pathlib import Path

import structlog
import yaml

# Initialize logger
logger = structlog.get_logger(__name__)


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file: str | None = None
    json_format: bool = False


@dataclass
class ESPNApiConfig:
    """ESPN API configuration."""

    base_url: str
    endpoints: dict[str, str]
    request_delay: float
    max_retries: int
    timeout: float
    historical_start_date: str | None = None
    batch_size: int = 50


@dataclass
class DataPathsConfig:
    """Data paths configuration."""

    bronze: str
    silver: str
    gold: str
    models: str


@dataclass
class SeasonsConfig:
    """Seasons configuration."""

    current: str
    historical: list[str]


@dataclass
class Config:
    """Main configuration object."""

    logging: LoggingConfig
    espn_api: ESPNApiConfig
    data_paths: DataPathsConfig
    seasons: SeasonsConfig


def get_config(config_dir: Path) -> Config:
    """Load configuration from YAML files in config directory.

    Args:
        config_dir: Path to configuration directory

    Returns:
        Config object with all settings
    """
    # Create default logging config
    logging_config = LoggingConfig()

    # Load data sources configuration
    data_sources_path = config_dir / "data_sources.yaml"
    if not data_sources_path.exists():
        logger.warning("Data sources configuration not found", path=str(data_sources_path))
        error_msg = f"Configuration file not found: {data_sources_path}"
        raise FileNotFoundError(error_msg)

    try:
        with open(data_sources_path) as f:
            data_sources = yaml.safe_load(f)
    except yaml.YAMLError as err:
        logger.exception("Invalid YAML in configuration file", error=str(err))
        error_msg = f"Configuration error in YAML: {err}"
        raise ValueError(error_msg) from err
    else:
        try:
            # Extract ESPN API config
            espn_api_config = ESPNApiConfig(
                base_url=data_sources["espn_api"]["base_url"],
                endpoints=data_sources["espn_api"]["endpoints"],
                request_delay=data_sources["espn_api"]["request_delay"],
                max_retries=data_sources["espn_api"]["max_retries"],
                timeout=data_sources["espn_api"]["timeout"],
                # Set defaults for historical_start_date and batch_size if not present
                historical_start_date=data_sources["espn_api"].get("historical_start_date"),
                batch_size=data_sources["espn_api"].get("batch_size", 50),
            )

            # Extract data paths config
            data_paths_config = DataPathsConfig(
                bronze=data_sources["data_paths"]["bronze"],
                silver=data_sources["data_paths"]["silver"],
                gold=data_sources["data_paths"]["gold"],
                models=data_sources["data_paths"]["models"],
            )

            # Extract seasons config
            seasons_config = SeasonsConfig(
                current=data_sources["seasons"]["current"],
                historical=data_sources["seasons"]["historical"],
            )

            # Create main config object
            config = Config(
                logging=logging_config,
                espn_api=espn_api_config,
                data_paths=data_paths_config,
                seasons=seasons_config,
            )

            return config
        except KeyError as err:
            logger.exception("Missing required configuration key", error=str(err))
            error_msg = f"Missing required configuration key: {err}"
            raise KeyError(error_msg) from err
        else:
            return config
