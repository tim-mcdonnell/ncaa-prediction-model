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

    def test_get_config_with_valid_file_returns_config(self, mocker):
        """Test that get_config returns configuration from a valid file."""
        # Arrange
        test_config = {
            "api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
            },
            "data": {"directory": "data"},
        }

        # Mock Path.exists to return True
        mocker.patch("pathlib.Path.exists", return_value=True)
        # Mock open to return a mock file
        with pytest.tmp_path() as config_dir:
            config_file = config_dir / "config.yaml"

            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

    def test_get_config_with_missing_config_file_raises_file_not_found_error(self):
        """Test handling a missing configuration file."""
        # Arrange
        with pytest.tmp_path(prefix=SECURE_TEMP_DIR_PREFIX) as non_existent_dir:
            # Remove the directory to ensure it doesn't exist
            if non_existent_dir.exists():
                non_existent_dir.rmdir()

            # Act & Assert
            with pytest.raises(FileNotFoundError, match="Config file not found"):
                get_config(non_existent_dir)

    def test_get_config_with_invalid_yaml_raises_error(self, mocker):
        """Test that get_config raises an error when YAML is invalid."""
        # Arrange
        invalid_yaml = "key: : invalid"

        # Mock Path.exists to return True
        mocker.patch("pathlib.Path.exists", return_value=True)
        # Mock open to return a mock file with invalid YAML
        with pytest.tmp_path() as config_dir:
            config_file = config_dir / "config.yaml"

            with open(config_file, "w") as f:
                f.write(invalid_yaml)

    def test_get_config_with_missing_key_raises_error(self, mocker):
        """Test that get_config raises an error when a required key is missing."""
        # Arrange
        incomplete_config = {
            "api": {"missing_base_url": "value"},
            "data": {"directory": "data"},
        }

        # Mock Path.exists to return True
        mocker.patch("pathlib.Path.exists", return_value=True)
        with pytest.tmp_path() as config_dir:
            config_file = config_dir / "config.yaml"

            with open(config_file, "w") as f:
                yaml.dump(incomplete_config, f)

    def test_get_config_with_minimal_required_keys_succeeds(self, mocker):
        """Test that get_config accepts configuration with only the minimal required keys."""
        # Arrange
        minimal_config = {
            "api": {
                "base_url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
            },
            "data": {"directory": "data"},
        }

        # Mock Path.exists to return True
        mocker.patch("pathlib.Path.exists", return_value=True)
        with pytest.tmp_path() as config_dir:
            config_file = config_dir / "config.yaml"

            with open(config_file, "w") as f:
                yaml.dump(minimal_config, f)
