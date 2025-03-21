"""Configuration utilities for the NCAA Basketball Prediction Model.

This module provides functionality for loading, validating, and accessing configuration
settings from YAML files. It includes support for configuring ESPN API access and
other system-wide settings.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union
from types import SimpleNamespace

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
    v3_base_url: str = ""
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


def get_default_config() -> Dict[str, Any]:
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
            "historical_start_date": None,
            "batch_size": 50,
        },
        "data_paths": {
            "bronze": "",
            "silver": "",
            "gold": "",
            "models": "",
        },
        "seasons": {
            "current": "",
            "historical": [],
        },
    }


def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
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


def dict_to_config(config_dict: Dict[str, Any]) -> SimpleNamespace:
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


def get_config(config_dir: Path) -> Any:
    """Load configuration from YAML files.

    Args:
        config_dir: Path to configuration directory

    Returns:
        Config object with merged configuration
    """
    # Ensure config directory exists
    if not config_dir.exists():
        raise FileNotFoundError(f"Configuration directory not found: {config_dir}")

    # Initialize with default config
    config_data = get_default_config()

    # Load all YAML files
    for yaml_file in config_dir.glob("*.yaml"):
        with open(yaml_file, "r") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                # Deep merge into config
                deep_merge(config_data, file_config)

    # Create config object
    config = dict_to_config(config_data)

    # Specially handle ESPN API config to create ESPNApiConfig objects
    if hasattr(config, "espn_api"):
        # Extract values for ESPNApiConfig
        base_url = config.espn_api.base_url
        endpoints = config.espn_api.endpoints
        
        # Get v3_base_url if it exists
        v3_base_url = getattr(config.espn_api, "v3_base_url", "")

        # Get other parameters or use defaults
        config.espn_api = ESPNApiConfig(
            base_url=base_url,
            endpoints=endpoints,
            v3_base_url=v3_base_url,
            initial_request_delay=getattr(config.espn_api, "initial_request_delay", 1.0),
            max_retries=getattr(config.espn_api, "max_retries", 3),
            timeout=getattr(config.espn_api, "timeout", 10.0),
            max_concurrency=getattr(config.espn_api, "max_concurrency", 5),
            min_request_delay=getattr(config.espn_api, "min_request_delay", 0.1),
            max_request_delay=getattr(config.espn_api, "max_request_delay", 5.0),
            backoff_factor=getattr(config.espn_api, "backoff_factor", 1.5),
            recovery_factor=getattr(config.espn_api, "recovery_factor", 0.9),
            error_threshold=getattr(config.espn_api, "error_threshold", 3),
            success_threshold=getattr(config.espn_api, "success_threshold", 10),
            historical_start_date=getattr(config.espn_api, "historical_start_date"),
            batch_size=getattr(config.espn_api, "batch_size", 50),
        )

    return config
