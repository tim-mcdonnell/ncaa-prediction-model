import copy
from typing import Any

import pytest
import yaml

from src.utils.config import Config, get_config

# Constants
DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_BATCH_SIZE = 20
DEFAULT_BATCH_SIZE_ALTERNATE = 50
SECURE_TEMP_DIR_PREFIX = "ncaa_prediction_test_config_"


class TestConfigModule:
    """Tests for the configuration module."""

    def test_get_config_with_valid_file_returns_config(self, tmp_path):
        """Test that get_config returns configuration from a valid file."""
        # Arrange
        valid_config: dict[str, Any] = {
            "logging": {
                "level": "INFO",
                "file": "logs/app.log",
                "json_format": True,
            },
            "espn_api": {
                "base_url": "https://example.com/api",
                "endpoints": {
                    "teams": "/teams",
                    "scoreboard": "/scoreboard",
                },
                "request_settings": {
                    "initial_request_delay": 0.5,
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
                "raw": "data/raw",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "models",
            },
            "seasons": {
                "current": "2022",
                "format": "YYYY",
            },
            "historical": {
                "start_season": "2001",
            },
        }

        # Create config directory and file
        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(valid_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        assert isinstance(result, Config)
        assert result.espn_api.base_url == valid_config["espn_api"]["base_url"]
        assert result.espn_api.endpoints == valid_config["espn_api"]["endpoints"]

        # Request settings
        rs = result.espn_api.request_settings
        assert (
            rs.initial_request_delay
            == valid_config["espn_api"]["request_settings"]["initial_request_delay"]
        )
        assert rs.max_retries == valid_config["espn_api"]["request_settings"]["max_retries"]
        assert rs.timeout == valid_config["espn_api"]["request_settings"]["timeout"]
        assert rs.batch_size == valid_config["espn_api"]["request_settings"]["batch_size"]

        # Data storage
        assert result.data_storage.raw == valid_config["data_storage"]["raw"]
        assert result.data_storage.silver == valid_config["data_storage"]["silver"]
        assert result.data_storage.gold == valid_config["data_storage"]["gold"]
        assert result.data_storage.models == valid_config["data_storage"]["models"]

        # Seasons
        assert result.seasons.current == valid_config["seasons"]["current"]
        assert result.seasons.format == valid_config["seasons"]["format"]

        # Historical
        assert result.historical.start_season == valid_config["historical"]["start_season"]

    def test_get_config_with_missing_config_file_raises_file_not_found_error(self, tmp_path):
        """Test handling a missing configuration file."""
        # Arrange - Create a directory but don't create the data_sources.yaml file
        config_dir = tmp_path / "non_existent_dir"
        config_dir.mkdir(exist_ok=True)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            get_config(config_dir)

    def test_get_config_with_invalid_yaml_raises_error(self, tmp_path):
        """Test that get_config raises an error when YAML is invalid."""
        # Arrange - Create a file with invalid YAML
        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            f.write("key: : invalid")

        # Act & Assert
        with pytest.raises(ValueError, match="Configuration error in YAML"):
            get_config(config_dir)

    def test_get_config_with_missing_key_raises_error(self, tmp_path):
        """Test that get_config raises an error when a required key is missing."""
        # Arrange - Create config with missing required key
        incomplete_config = {
            "espn_api": {
                # Missing base_url
                "endpoints": {"scoreboard": "scoreboard"},
                "request_settings": {
                    "initial_request_delay": 0.5,
                    "max_retries": 3,
                    "timeout": 10.0,
                },
            },
            "data_storage": {
                "raw": "data/raw",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "models",
            },
            "seasons": {"current": "2022", "format": "YYYY"},
            "historical": {"start_season": "2001"},
        }

        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(incomplete_config, f)

        # Act & Assert
        with pytest.raises(KeyError, match="Missing required configuration key"):
            get_config(config_dir)

    def test_get_config_with_minimal_required_keys_succeeds(self, tmp_path):
        """Test that get_config accepts configuration with only the minimal required keys."""
        # Arrange
        minimal_config = {
            "espn_api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
                "endpoints": {"scoreboard": "scoreboard"},
                "request_settings": {
                    "initial_request_delay": 0.5,
                    "max_retries": 3,
                    "timeout": 10.0,
                },
            },
            "data_storage": {
                "raw": "data/raw",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "models",
            },
            "seasons": {"current": "2022", "format": "YYYY"},
            "historical": {"start_season": "2001"},
        }

        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(minimal_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        espn_api = result.espn_api
        data_storage = result.data_storage
        seasons = result.seasons

        assert espn_api.base_url == minimal_config["espn_api"]["base_url"]  # type: ignore
        assert data_storage.raw == minimal_config["data_storage"]["raw"]  # type: ignore
        assert seasons.current == minimal_config["seasons"]["current"]  # type: ignore

    def test_get_config_with_extra_keys_succeeds(self, tmp_path):
        """Test that get_config succeeds with extra keys."""
        # Arrange
        valid_config = {
            "espn_api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
                "endpoints": {"scoreboard": "scoreboard", "teams": "teams"},
                "request_settings": {
                    "initial_request_delay": 0.5,
                    "max_retries": 3,
                    "timeout": 10.0,
                    "batch_size": 20,
                },
            },
            "data_storage": {
                "raw": "data/raw",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "models",
            },
            "seasons": {"current": "2022", "format": "YYYY"},
            "historical": {"start_season": "2001"},
        }

        extra_config = copy.deepcopy(valid_config)
        extra_config["extra_section"] = {"key": "value"}

        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(extra_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        espn_api = result.espn_api
        data_storage = result.data_storage
        seasons = result.seasons

        assert espn_api.base_url == valid_config["espn_api"]["base_url"]  # type: ignore
        assert data_storage.raw == valid_config["data_storage"]["raw"]  # type: ignore
        assert seasons.current == valid_config["seasons"]["current"]  # type: ignore

    def test_get_config_with_merged_config(self, tmp_path):
        """Test that get_config accepts a merged configuration."""
        # Test with merged
        merged_config = {
            "logging": {
                "level": "DEBUG",
                "file": None,
                "json_format": False,
            },
            "espn_api": {
                "base_url": "https://example.com/api",
                "endpoints": {
                    "teams": "/teams",
                    "scoreboard": "/scoreboard",
                },
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
                "raw": "/data/bronze",
                "silver": "/data/silver",
                "gold": "/data/gold",
                "models": "/models",
            },
            "seasons": {
                "current": "2022",
                "format": "YYYY",
            },
            "historical": {
                "start_season": "2001",
            },
        }

        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(merged_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        espn_api = result.espn_api
        data_storage = result.data_storage
        seasons = result.seasons

        assert espn_api.base_url == merged_config["espn_api"]["base_url"]  # type: ignore
        assert data_storage.raw == merged_config["data_storage"]["raw"]  # type: ignore
        assert seasons.current == merged_config["seasons"]["current"]  # type: ignore
