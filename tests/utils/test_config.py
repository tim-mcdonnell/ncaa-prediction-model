import pytest
import os
import tempfile
from pathlib import Path
import yaml
from unittest.mock import patch, mock_open

from src.utils.config import get_config, Config, ESPNApiConfig, DataPathsConfig, SeasonsConfig, LoggingConfig

class TestConfigModule:
    """Tests for the configuration module."""
    
    def test_get_config_WithValidYamlFile_ReturnsConfigObject(self):
        """Test loading a valid configuration file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir)
            config_file = config_dir / "data_sources.yaml"
            
            # Create a valid config file
            config_data = {
                "espn_api": {
                    "base_url": "https://test.api.com",
                    "endpoints": {
                        "scoreboard": "/test/scoreboard",
                        "teams": "/test/teams"
                    },
                    "request_delay": 0.5,
                    "max_retries": 2,
                    "timeout": 5.0,
                    "historical_start_date": "2023-01-01",
                    "batch_size": 20
                },
                "data_paths": {
                    "bronze": "test/bronze",
                    "silver": "test/silver",
                    "gold": "test/gold",
                    "models": "test/models"
                },
                "seasons": {
                    "current": "2023-24",
                    "historical": ["2022-23", "2021-22"]
                }
            }
            
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
            
            # Act
            config = get_config(config_dir)
            
            # Assert
            assert isinstance(config, Config)
            assert config.espn_api.base_url == "https://test.api.com"
            assert config.espn_api.request_delay == 0.5
            assert config.espn_api.historical_start_date == "2023-01-01"
            assert config.espn_api.batch_size == 20
            assert config.data_paths.bronze == "test/bronze"
            assert config.seasons.current == "2023-24"
            assert "2022-23" in config.seasons.historical
    
    def test_get_config_WithMissingConfigFile_RaisesFileNotFoundError(self):
        """Test handling a missing configuration file."""
        # Arrange
        non_existent_dir = Path("/tmp/non_existent_dir_" + str(os.getpid()))
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            get_config(non_existent_dir)
    
    def test_get_config_WithInvalidYamlSyntax_RaisesValueError(self):
        """Test handling invalid YAML syntax."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir)
            config_file = config_dir / "data_sources.yaml"
            
            # Create an invalid YAML file
            with open(config_file, "w") as f:
                f.write("invalid: yaml: file: with extra colons")
            
            # Act & Assert
            with pytest.raises(ValueError):
                get_config(config_dir)
    
    def test_get_config_WithMissingRequiredField_RaisesKeyError(self):
        """Test handling missing required fields."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir)
            config_file = config_dir / "data_sources.yaml"
            
            # Create config missing required fields
            config_data = {
                # Missing espn_api
                "data_paths": {
                    "bronze": "test/bronze",
                    "silver": "test/silver",
                    "gold": "test/gold",
                    "models": "test/models"
                },
                "seasons": {
                    "current": "2023-24",
                    "historical": ["2022-23", "2021-22"]
                }
            }
            
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
            
            # Act & Assert
            with pytest.raises(ValueError):
                get_config(config_dir)
    
    def test_get_config_WithOptionalFieldsOmitted_UsesDefaultValues(self):
        """Test that optional fields use default values when omitted."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir)
            config_file = config_dir / "data_sources.yaml"
            
            # Create config with optional fields omitted
            config_data = {
                "espn_api": {
                    "base_url": "https://test.api.com",
                    "endpoints": {
                        "scoreboard": "/test/scoreboard",
                        "teams": "/test/teams"
                    },
                    "request_delay": 0.5,
                    "max_retries": 2,
                    "timeout": 5.0
                    # historical_start_date and batch_size omitted
                },
                "data_paths": {
                    "bronze": "test/bronze",
                    "silver": "test/silver",
                    "gold": "test/gold",
                    "models": "test/models"
                },
                "seasons": {
                    "current": "2023-24",
                    "historical": ["2022-23", "2021-22"]
                }
            }
            
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
            
            # Act
            config = get_config(config_dir)
            
            # Assert
            assert config.espn_api.historical_start_date is None
            assert config.espn_api.batch_size == 50  # Default value 