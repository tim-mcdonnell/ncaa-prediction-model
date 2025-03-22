"""Configuration utilities for the NCAA Basketball Prediction Model.

This module provides functionality for loading, validating, and accessing configuration
settings from YAML files. It includes support for configuring ESPN API access and
other system-wide settings.
"""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
class RequestSettings:
    """ESPN API request settings."""

    initial_request_delay: float = 1.0
    max_retries: int = 3
    timeout: float = 10.0
    max_concurrency: int = 5
    min_request_delay: float = 0.1
    max_request_delay: float = 5.0
    backoff_factor: float = 1.5
    recovery_factor: float = 0.9
    error_threshold: int = 3
    success_threshold: int = 10
    batch_size: int = 50


@dataclass
class ESPNApiConfig:
    """ESPN API configuration."""

    base_url: str
    endpoints: dict[str, str]
    v3_base_url: str = ""
    request_settings: RequestSettings = None

    def __post_init__(self):
        """Initialize default request settings if none provided."""
        if self.request_settings is None:
            self.request_settings = RequestSettings()


@dataclass
class DataStorageConfig:
    """Data storage configuration."""

    raw: str
    silver: str
    gold: str
    models: str


@dataclass
class SeasonsConfig:
    """Seasons configuration."""

    current: str
    format: str = "YYYY"


@dataclass
class HistoricalConfig:
    """Historical data configuration."""

    start_season: str

    def get_start_date(self) -> str:
        """Derive the start date from the start season.

        Returns:
            Start date in YYYY-MM-DD format, set to June 1st of the start season year
        """
        return f"{self.start_season}-06-01"


@dataclass
class Config:
    """Main configuration object."""

    logging: LoggingConfig
    espn_api: ESPNApiConfig
    data_storage: DataStorageConfig
    seasons: SeasonsConfig
    historical: HistoricalConfig


def get_default_config() -> dict[str, Any]:
    """Get default configuration settings.

    Returns:
        Dictionary with default configuration values
    """
    return {
        "logging": {
            "level": "INFO",
            "file": None,
            "json_format": False,
        },
        "espn_api": {
            "base_url": "",
            "endpoints": {},
            "v3_base_url": "",
            "request_settings": {
                "initial_request_delay": 1.0,
                "max_retries": 3,
                "timeout": 10.0,
                "max_concurrency": 5,
                "min_request_delay": 0.1,
                "max_request_delay": 5.0,
                "backoff_factor": 1.5,
                "recovery_factor": 0.9,
                "error_threshold": 3,
                "success_threshold": 10,
                "batch_size": 50,
            },
        },
        "data_storage": {
            "raw": "",
            "silver": "",
            "gold": "",
            "models": "",
        },
        "seasons": {
            "current": "",
            "format": "YYYY",
        },
        "historical": {
            "start_season": "",
        },
    }


def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries recursively.

    Args:
        target: Target dictionary to merge into
        source: Source dictionary to merge from

    Returns:
        Merged dictionary
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def dict_to_config(config_dict: dict[str, Any]) -> SimpleNamespace:
    """Convert a nested dictionary to a SimpleNamespace object recursively.

    Args:
        config_dict: Dictionary to convert

    Returns:
        SimpleNamespace object with attributes from dictionary
    """
    namespace = SimpleNamespace()
    for key, value in config_dict.items():
        if isinstance(value, dict):
            setattr(namespace, key, dict_to_config(value))
        else:
            setattr(namespace, key, value)
    return namespace


def get_config(config_dir: Path) -> Config:
    """Load configuration from YAML files.

    Args:
        config_dir: Path to configuration directory

    Returns:
        Config object with merged configuration

    Raises:
        FileNotFoundError: If configuration directory or file not found
        ValueError: If configuration YAML is invalid
        KeyError: If required configuration key is missing
    """
    # Ensure config directory exists
    if not config_dir.exists():
        raise FileNotFoundError(f"Configuration directory not found: {config_dir}")

    # Check for data_sources.yaml
    data_sources_file = config_dir / "data_sources.yaml"
    if not data_sources_file.exists():
        raise FileNotFoundError("Configuration file not found: data_sources.yaml")

    # Initialize with default config
    config_data = get_default_config()

    # Load all YAML files
    try:
        for yaml_file in config_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Deep merge into config
                    deep_merge(config_data, file_config)
    except yaml.YAMLError as e:
        raise ValueError(f"Configuration error in YAML: {e}") from e

    # Validate configuration
    validate_config(config_data)

    # Extract sections
    logging_config = LoggingConfig(**config_data.get("logging", {}))

    # Process ESPN API config
    espn_api_data = config_data.get("espn_api", {})
    if not espn_api_data.get("base_url"):
        raise KeyError("Missing required configuration key: espn_api.base_url")
    if not espn_api_data.get("endpoints"):
        raise KeyError("Missing required configuration key: espn_api.endpoints")

    # Process request settings
    request_settings_data = espn_api_data.get("request_settings", {})
    request_settings = RequestSettings(**request_settings_data)

    # Create ESPN API config
    espn_api_config = ESPNApiConfig(
        base_url=espn_api_data["base_url"],
        endpoints=espn_api_data["endpoints"],
        v3_base_url=espn_api_data.get("v3_base_url", ""),
        request_settings=request_settings,
    )

    # Process data storage config
    data_storage_data = config_data.get("data_storage", {})
    if not all(key in data_storage_data for key in ["raw", "silver", "gold", "models"]):
        raise KeyError("Missing required configuration key in data_storage")
    data_storage_config = DataStorageConfig(**data_storage_data)

    # Process seasons config
    seasons_data = config_data.get("seasons", {})
    if "current" not in seasons_data:
        raise KeyError("Missing required configuration key: seasons.current")
    seasons_config = SeasonsConfig(**seasons_data)

    # Process historical config
    historical_data = config_data.get("historical", {})
    if not all(key in historical_data for key in ["start_season"]):
        raise KeyError("Missing required configuration key in historical")
    historical_config = HistoricalConfig(**historical_data)

    # Create and return the Config object
    return Config(
        logging=logging_config,
        espn_api=espn_api_config,
        data_storage=data_storage_config,
        seasons=seasons_config,
        historical=historical_config,
    )


def validate_config(config_data: dict[str, Any]) -> None:
    """Validate configuration data.

    Args:
        config_data: Configuration data dictionary

    Raises:
        KeyError: If required configuration key is missing
    """
    # Check required top-level sections
    required_sections = ["espn_api", "data_storage", "seasons", "historical"]
    for section in required_sections:
        if section not in config_data:
            raise KeyError(f"Missing required configuration key: {section}")
