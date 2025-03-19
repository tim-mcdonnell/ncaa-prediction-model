---
title: Configuration Management
description: Strategy for managing configuration in the NCAA Basketball Prediction Model
---

# Configuration Management

This document outlines the approach to configuration management in the NCAA Basketball Prediction Model, ensuring a consistent and flexible way to handle settings without hardcoding values.

## Configuration Principles

1. **Separation of Concerns**: Configuration is separated from code
2. **Environment Awareness**: Different settings for different environments
3. **Minimal Redundancy**: Each setting defined in exactly one place
4. **Appropriate Defaults**: Sensible defaults where possible
5. **Type Safety**: Configuration values have explicit types and validation

## Configuration Sources

Configuration is loaded from these sources in order of precedence (highest to lowest):

1. **Environment Variables**: For sensitive data and deployment-specific settings
2. **Command Line Arguments**: For runtime overrides
3. **Configuration Files**: For default and shared settings
4. **Code Defaults**: As fallbacks where appropriate

## Configuration Structure

### YAML Configuration Files

Configuration files are stored in the `config/` directory using YAML format:

```yaml
# config/data_sources.yaml
espn_api:
  base_url: "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
  endpoints:
    teams: "/teams"
    team_detail: "/teams/{team_id}"
    scoreboard: "/scoreboard"
  request_delay: 1.0  # seconds between requests
  max_retries: 3
  timeout: 10.0  # seconds

# config/processing.yaml
data_paths:
  bronze: "data/bronze"
  silver: "data/silver"
  gold: "data/gold"
  models: "models"

batch_size: 100
workers: 4

# config/logging.yaml
logging:
  level: "INFO"
  file: "logs/app.log"
  json_format: false
```

### Environment Variables

Environment variables override configuration file values using this pattern:

- `NCAA_` prefix for all project variables
- Upper case with underscores
- Double underscore for nested values

Examples:
- `NCAA_ESPN_API_REQUEST_DELAY=2.0`
- `NCAA_DATA_PATHS__BRONZE=/mnt/data/bronze`
- `NCAA_LOGGING__LEVEL=DEBUG`

## Configuration Manager

A centralized ConfigManager handles loading and accessing configuration:

```python
from pathlib import Path
from typing import Any, Dict, Optional, Union
import os
import yaml
from pydantic import BaseModel

class EspnApiConfig(BaseModel):
    base_url: str
    endpoints: Dict[str, str]
    request_delay: float
    max_retries: int
    timeout: float

class DataPathsConfig(BaseModel):
    bronze: str
    silver: str
    gold: str
    models: str

class LoggingConfig(BaseModel):
    level: str
    file: Optional[str] = None
    json_format: bool = False

class AppConfig(BaseModel):
    espn_api: EspnApiConfig
    data_paths: DataPathsConfig
    logging: LoggingConfig
    batch_size: int = 100
    workers: int = 4

class ConfigManager:
    """Manages application configuration from multiple sources."""

    def __init__(self, config_dir: Union[str, Path] = "config"):
        self.config_dir = Path(config_dir)
        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """Load configuration from files and environment variables."""
        if self._config is not None:
            return self._config

        # Load configuration files
        config_data = {}
        for config_file in self.config_dir.glob("*.yaml"):
            with open(config_file, "r") as f:
                # Use filename without extension as the top-level key
                key = config_file.stem
                config_data[key] = yaml.safe_load(f)

        # Flatten the dictionary for easier environment variable override
        flat_config = self._flatten_dict(config_data)

        # Override with environment variables
        for key, value in os.environ.items():
            if key.startswith("NCAA_"):
                # Convert from environment variable format to config key
                config_key = key[5:].lower().replace("__", ".")  # Remove NCAA_ prefix
                flat_config[config_key] = self._convert_value_type(value, flat_config.get(config_key))

        # Unflatten back to nested structure
        config_dict = self._unflatten_dict(flat_config)

        # Create validated config object
        self._config = AppConfig(**config_dict)
        return self._config

    @property
    def config(self) -> AppConfig:
        """Get the current configuration, loading it if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        """Flatten nested dictionaries with keys joined by separator."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _unflatten_dict(self, d: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
        """Unflatten dictionary with keys split by separator."""
        result = {}
        for key, value in d.items():
            parts = key.split(sep)
            curr = result
            for part in parts[:-1]:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = value
        return result

    def _convert_value_type(self, value: str, reference_value: Any) -> Any:
        """Convert string value to appropriate type based on reference value."""
        if reference_value is None:
            return value

        if isinstance(reference_value, bool):
            return value.lower() in ("true", "yes", "1", "t", "y")
        elif isinstance(reference_value, int):
            return int(value)
        elif isinstance(reference_value, float):
            return float(value)
        elif isinstance(reference_value, list):
            return value.split(",")
        return value
```

## Usage Patterns

### Global Configuration Access

The ConfigManager is initialized once at application startup and provides a singleton for accessing config:

```python
# src/utils/config.py

from pathlib import Path
from typing import Optional

# ConfigManager class definition (as above)...

# Singleton instance
_config_manager: Optional[ConfigManager] = None

def get_config_manager(config_dir: str = "config") -> ConfigManager:
    """Get the singleton ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager

def get_config():
    """Get the current application configuration."""
    return get_config_manager().config
```

### Using Configuration in Code

Import the configuration in modules where needed:

```python
from utils.config import get_config

def fetch_team_data(team_id: str):
    config = get_config()
    base_url = config.espn_api.base_url
    endpoint = config.espn_api.endpoints["team_detail"].format(team_id=team_id)
    url = f"{base_url}{endpoint}"

    # Use other config values
    timeout = config.espn_api.timeout
    max_retries = config.espn_api.max_retries

    # Implementation...
```

### Command Line Overrides

CLI arguments can override configuration values:

```python
import argparse
from utils.config import get_config_manager

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, help="Batch size for processing")
    parser.add_argument("--workers", type=int, help="Number of worker processes")
    args = parser.parse_args()

    # Load baseline config
    config_manager = get_config_manager()
    config = config_manager.load_config()

    # Override with command line arguments if provided
    if args.batch_size is not None:
        config.batch_size = args.batch_size
    if args.workers is not None:
        config.workers = args.workers
```

## Configuration Management Best Practices

1. **Never Hardcode Values**: Always use the configuration system for settings
2. **Use Typed Validation**: Ensure configuration values have correct types
3. **Document Each Setting**: Comment each configuration setting in YAML files
4. **Namespace Environment Variables**: Use the `NCAA_` prefix to avoid conflicts
5. **Provide Defaults**: Include sensible defaults for most settings
6. **Keep Sensitive Data Separate**: Use environment variables for API keys, etc.
7. **Test With Different Configurations**: Ensure the application works with various settings
