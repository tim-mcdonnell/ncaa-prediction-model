---
title: Configuration Management
description: Configuration management strategy for the NCAA Basketball Prediction Model
---

# Configuration Management

This document describes the configuration management strategy for the NCAA Basketball Prediction Model.

## Principles

The configuration system follows these core principles:

1. **Separation of Concerns**: Different aspects of the application are configured separately.
2. **Environment Awareness**: Configuration adapts to different environments (development, testing, production).
3. **Minimal Redundancy**: Configuration values are defined once and shared.
4. **Appropriate Defaults**: Sensible defaults with the ability to override.
5. **Type Safety**: Configuration values have well-defined types.

## Configuration Sources

Configuration is loaded from multiple sources in this order of precedence:

1. Environment Variables
2. Command Line Arguments
3. Configuration Files
4. Code Defaults

## File Structure

YAML configuration files are stored in the `config/` directory:

```
config/
├── default.yaml                # Default configuration for all environments
├── development.yaml            # Development-specific overrides
├── testing.yaml                # Testing-specific overrides
├── production.yaml             # Production-specific overrides
├── local.yaml                  # Local overrides (git-ignored)
└── .env                        # Environment variables (git-ignored)
```

## Configuration Schema

The configuration uses a hierarchical structure:

```yaml
# Example configuration structure
espn_api:
  base_url: "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
  user_agent: "Mozilla/5.0"
  cache_dir: "./cache/espn"
  rate_limit: 5  # requests per second
  timeout: 30  # seconds

storage:
  bronze_dir: "./data/raw"
  silver_dir: "./data/processed"
  gold_dir: "./data/features"
  model_dir: "./models"
  duckdb_path: "./data/ncaa.duckdb"

logging:
  level: "INFO"
  format: "%(asctime)s [%(levelname)s] %(message)s"
  file: "./logs/ncaa.log"
```

## Ingestion Configuration

The ingestion system uses a hierarchical configuration model:

### BaseIngestionConfig

The abstract base configuration class that all endpoint-specific configurations inherit from:

```python
@dataclass
class BaseIngestionConfig:
    """Base configuration for all ingestion operations."""

    # API configuration
    espn_api_config: ESPNApiConfig

    # Data storage configuration
    parquet_dir: str = ""  # Directory where Parquet files will be stored

    # Processing options
    force_check: bool = False  # Force API requests even when data might exist
    force_overwrite: bool = False  # Force overwrite of existing data

    # Concurrency options
    concurrency: Optional[int] = None  # Number of concurrent operations
```

### ESPNApiConfig

The API-specific configuration that's shared across all ESPN API endpoints:

```python
@dataclass
class ESPNApiConfig:
    """Configuration for ESPN API access."""

    base_url: str = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
    cache_dir: str = "./cache/espn"
    user_agent: str = "Mozilla/5.0"
    rate_limit: float = 5.0  # requests per second
    timeout: int = 30  # seconds
    default_params: Dict[str, Any] = field(default_factory=dict)
```

### Endpoint-Specific Configurations

Each endpoint has its own configuration class that extends BaseIngestionConfig:

#### ScoreboardIngestionConfig

```python
@dataclass
class ScoreboardIngestionConfig(BaseIngestionConfig):
    """Configuration for scoreboard data ingestion."""

    # Date selection parameters (only one should be used)
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    yesterday: bool = False
    today: bool = False
    seasons: Optional[List[str]] = None
    year: Optional[int] = None
```

#### TeamsIngestionConfig

```python
@dataclass
class TeamsIngestionConfig(BaseIngestionConfig):
    """Configuration for teams data ingestion."""

    # Season parameters
    seasons: Optional[List[str]] = None

    # Optional filters
    conference: Optional[str] = None

    # Pagination parameters
    limit: int = 100
    page: int = 1
```

#### UnifiedIngestionConfig

For ingesting multiple endpoints in a single operation:

```python
@dataclass
class UnifiedIngestionConfig(BaseIngestionConfig):
    """Configuration for unified multi-endpoint ingestion."""

    # Endpoints to ingest
    endpoints: List[str] = None

    # Endpoint-specific parameters
    # These fields include all parameters from endpoint-specific configs

    # Global concurrency control
    max_parallel_endpoints: int = 2
```

## ConfigManager Class

A centralized `ConfigManager` class handles loading and accessing configuration:

```python
class ConfigManager:
    """Manages configuration for the NCAA Basketball Prediction Model."""

    def __init__(self, config_dir: str = "./config") -> None:
        """Initialize the configuration manager."""
        self.config_dir = config_dir
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from files and environment variables."""
        # Load base configuration
        config = self._load_yaml("default.yaml")

        # Load environment-specific configuration
        env = os.environ.get("NCAA_ENV", "development")
        env_config = self._load_yaml(f"{env}.yaml")
        self._merge_config(config, env_config)

        # Load local overrides if they exist
        local_config = self._load_yaml("local.yaml")
        self._merge_config(config, local_config)

        # Override with environment variables
        self._override_from_env(config)

        return config

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file."""
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            return {}

        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override into base config."""
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _override_from_env(self, config: Dict[str, Any]) -> None:
        """Override configuration from environment variables."""
        for key, value in os.environ.items():
            if not key.startswith("NCAA_"):
                continue

            # Convert NCAA_API_BASE_URL to ['api', 'base_url']
            path = key[5:].lower().split('_')
            self._set_nested_value(config, path, value)

    def _set_nested_value(self, config: Dict[str, Any], path: List[str], value: str) -> None:
        """Set a value in nested configuration using a path."""
        current = config
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Convert value to appropriate type based on reference value
        key = path[-1]
        if key in current:
            ref_value = current[key]
            if isinstance(ref_value, bool):
                value = value.lower() in ('true', 'yes', '1')
            elif isinstance(ref_value, int):
                value = int(value)
            elif isinstance(ref_value, float):
                value = float(value)

        current[key] = value

    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        parts = path.split('.')
        current = self.config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def create_espn_api_config(self) -> ESPNApiConfig:
        """Create an ESPN API configuration from the loaded config."""
        api_config = self.get('espn_api', {})
        return ESPNApiConfig(
            base_url=api_config.get('base_url', ESPNApiConfig.base_url),
            cache_dir=api_config.get('cache_dir', ESPNApiConfig.cache_dir),
            user_agent=api_config.get('user_agent', ESPNApiConfig.user_agent),
            rate_limit=api_config.get('rate_limit', ESPNApiConfig.rate_limit),
            timeout=api_config.get('timeout', ESPNApiConfig.timeout),
            default_params=api_config.get('default_params', {})
        )

    def create_scoreboard_config(self, **overrides) -> ScoreboardIngestionConfig:
        """Create a scoreboard ingestion configuration."""
        return ScoreboardIngestionConfig(
            espn_api_config=self.create_espn_api_config(),
            parquet_dir=self.get('storage.bronze_dir', ''),
            **overrides
        )

    def create_teams_config(self, **overrides) -> TeamsIngestionConfig:
        """Create a teams ingestion configuration."""
        return TeamsIngestionConfig(
            espn_api_config=self.create_espn_api_config(),
            parquet_dir=self.get('storage.bronze_dir', ''),
            **overrides
        )

    def create_unified_config(self, **overrides) -> UnifiedIngestionConfig:
        """Create a unified ingestion configuration."""
        return UnifiedIngestionConfig(
            espn_api_config=self.create_espn_api_config(),
            parquet_dir=self.get('storage.bronze_dir', ''),
            **overrides
        )
```

## Usage Patterns

### Accessing the Global Configuration

```python
from src.utils.config import get_config

# Access a configuration value
base_url = get_config().get('espn_api.base_url')

# Access a nested configuration with default
timeout = get_config().get('espn_api.timeout', 30)
```

### Command Line Overrides

Command line arguments take precedence over configuration files:

```python
@click.command()
@click.option('--date', help='Date to fetch data for')
@click.option('--force-check', is_flag=True, help='Force check for data changes')
def ingest_scoreboard(date, force_check):
    """Ingest scoreboard data."""
    # Create configuration with command line overrides
    config = get_config().create_scoreboard_config(
        date=date,
        force_check=force_check
    )

    # Use the configuration
    result = ingest_scoreboard(config)
```

### Configuring in Tests

Tests can provide custom configuration:

```python
def test_ingest_scoreboard():
    """Test ingesting scoreboard data."""
    # Create a test-specific configuration
    config = ScoreboardIngestionConfig(
        espn_api_config=ESPNApiConfig(
            base_url="https://test-url.com",
            cache_dir=tmp_path,
            timeout=1
        ),
        date="2023-03-15",
        parquet_dir=tmp_path,
        force_check=True
    )

    # Run the function with test configuration
    result = ingest_scoreboard(config)

    # Assert expected results
    assert len(result) > 0
```

## Configuration Migration

When making changes to configuration values or structure, follow these steps:

1. Add the new configuration value alongside existing ones
2. Deprecate the old value with a warning
3. Update code to use the new value
4. Remove the deprecated value in a future release

Example of deprecation:

```python
def get_api_url():
    if 'api_url' in config:
        warnings.warn("'api_url' is deprecated, use 'espn_api.base_url' instead", DeprecationWarning)
        return config['api_url']
    return config['espn_api']['base_url']
```
