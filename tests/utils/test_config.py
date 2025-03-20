import copy

import pytest
import yaml

from src.utils.config import get_config

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
        valid_config = {
            "espn_api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
                "endpoints": {"scoreboard": "scoreboard", "teams": "teams"},
                "request_delay": 0.5,
                "max_retries": 3,
                "timeout": 10.0,
                "batch_size": 20,
            },
            "data_paths": {
                "bronze": "data/bronze",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "data/models",
            },
            "seasons": {"current": "2022-23", "historical": ["2021-22", "2020-21"]},
        }

        # Create config directory and file
        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(valid_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        espn_api = result.espn_api
        data_paths = result.data_paths
        seasons = result.seasons

        assert espn_api.base_url == valid_config["espn_api"]["base_url"]  # type: ignore
        assert espn_api.endpoints == valid_config["espn_api"]["endpoints"]  # type: ignore
        assert espn_api.request_delay == valid_config["espn_api"]["request_delay"]  # type: ignore
        assert data_paths.bronze == valid_config["data_paths"]["bronze"]  # type: ignore
        assert seasons.current == valid_config["seasons"]["current"]  # type: ignore

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
                "request_delay": 0.5,
                "max_retries": 3,
                "timeout": 10.0,
            },
            "data_paths": {
                "bronze": "data/bronze",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "data/models",
            },
            "seasons": {"current": "2022-23", "historical": ["2021-22", "2020-21"]},
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
                "request_delay": 0.5,
                "max_retries": 3,
                "timeout": 10.0,
            },
            "data_paths": {
                "bronze": "data/bronze",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "data/models",
            },
            "seasons": {"current": "2022-23", "historical": ["2021-22"]},
        }

        config_dir = tmp_path
        data_sources_file = config_dir / "data_sources.yaml"

        with open(data_sources_file, "w") as f:
            yaml.dump(minimal_config, f)

        # Act
        result = get_config(config_dir)

        # Assert
        espn_api = result.espn_api
        data_paths = result.data_paths
        seasons = result.seasons

        assert espn_api.base_url == minimal_config["espn_api"]["base_url"]  # type: ignore
        assert data_paths.bronze == minimal_config["data_paths"]["bronze"]  # type: ignore
        assert seasons.current == minimal_config["seasons"]["current"]  # type: ignore

    def test_get_config_with_extra_keys_succeeds(self, tmp_path):
        """Test that get_config succeeds with extra keys."""
        # Arrange
        valid_config = {
            "espn_api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
                "endpoints": {"scoreboard": "scoreboard", "teams": "teams"},
                "request_delay": 0.5,
                "max_retries": 3,
                "timeout": 10.0,
                "batch_size": 20,
            },
            "data_paths": {
                "bronze": "data/bronze",
                "silver": "data/silver",
                "gold": "data/gold",
                "models": "data/models",
            },
            "seasons": {"current": "2022-23", "historical": ["2021-22", "2020-21"]},
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
        data_paths = result.data_paths
        seasons = result.seasons

        assert espn_api.base_url == valid_config["espn_api"]["base_url"]  # type: ignore
        assert data_paths.bronze == valid_config["data_paths"]["bronze"]  # type: ignore
        assert seasons.current == valid_config["seasons"]["current"]  # type: ignore
