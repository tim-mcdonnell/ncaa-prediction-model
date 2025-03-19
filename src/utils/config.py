from pathlib import Path
import yaml
from typing import Any, Dict, List, Optional, Union
import structlog
from dataclasses import dataclass

# Initialize logger
logger = structlog.get_logger(__name__)

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: Optional[str] = None
    json_format: bool = False

@dataclass
class ESPNApiConfig:
    """ESPN API configuration."""
    base_url: str
    endpoints: Dict[str, str]
    request_delay: float
    max_retries: int
    timeout: float
    historical_start_date: Optional[str] = None
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
    historical: List[str]

@dataclass
class Config:
    """Main configuration object."""
    logging: LoggingConfig
    espn_api: ESPNApiConfig
    data_paths: DataPathsConfig
    seasons: SeasonsConfig

def get_config(config_dir: Path) -> Config:
    """
    Load configuration from YAML files in config directory.
    
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
        raise FileNotFoundError(f"Configuration file not found: {data_sources_path}")
    
    try:
        with open(data_sources_path, "r") as f:
            data_sources = yaml.safe_load(f)
            
        # Extract ESPN API config
        espn_api_config = ESPNApiConfig(
            base_url=data_sources["espn_api"]["base_url"],
            endpoints=data_sources["espn_api"]["endpoints"],
            request_delay=data_sources["espn_api"]["request_delay"],
            max_retries=data_sources["espn_api"]["max_retries"],
            timeout=data_sources["espn_api"]["timeout"],
            # Set defaults for historical_start_date and batch_size if not present
            historical_start_date=data_sources["espn_api"].get("historical_start_date"),
            batch_size=data_sources["espn_api"].get("batch_size", 50)
        )
        
        # Extract data paths config
        data_paths_config = DataPathsConfig(
            bronze=data_sources["data_paths"]["bronze"],
            silver=data_sources["data_paths"]["silver"],
            gold=data_sources["data_paths"]["gold"],
            models=data_sources["data_paths"]["models"]
        )
        
        # Extract seasons config
        seasons_config = SeasonsConfig(
            current=data_sources["seasons"]["current"],
            historical=data_sources["seasons"]["historical"]
        )
        
        # Create main config object
        config = Config(
            logging=logging_config,
            espn_api=espn_api_config,
            data_paths=data_paths_config,
            seasons=seasons_config
        )
        
        return config
        
    except (KeyError, yaml.YAMLError) as e:
        logger.error("Failed to load configuration", error=str(e))
        raise ValueError(f"Configuration error: {e}") 