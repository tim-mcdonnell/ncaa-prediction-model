import pytest
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.utils.logging import configure_logging

class TestLoggingModule:
    """Tests for the logging utility module."""
    
    def test_configure_logging_WithDefaultParams_ConfiguresCorrectly(self):
        """Test configure_logging with default parameters."""
        # Arrange
        with patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
             patch("src.utils.logging.structlog.configure") as mock_structlog_configure:
            
            # Act
            configure_logging()
            
            # Assert
            mock_basic_config.assert_called_once()
            assert mock_basic_config.call_args[1]["level"] == logging.INFO
            
            # Check that structlog.configure was called with processors
            mock_structlog_configure.assert_called_once()
            processors = mock_structlog_configure.call_args[1]["processors"]
            assert len(processors) > 0
    
    def test_configure_logging_WithCustomLogLevel_SetsCorrectLevel(self):
        """Test configure_logging with custom log level."""
        # Arrange
        with patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
             patch("src.utils.logging.structlog.configure") as mock_structlog_configure:
            
            # Act
            configure_logging(log_level="DEBUG")
            
            # Assert
            mock_basic_config.assert_called_once()
            assert mock_basic_config.call_args[1]["level"] == logging.DEBUG
    
    def test_configure_logging_WithInvalidLogLevel_RaisesAttributeError(self):
        """Test configure_logging with invalid log level raises AttributeError."""
        # Arrange & Act & Assert
        with patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
             patch("src.utils.logging.structlog.configure") as mock_structlog_configure:
            
            with pytest.raises(AttributeError):
                configure_logging(log_level="INVALID_LEVEL")
    
    def test_configure_logging_WithJsonLogsTrue_ConfiguresJsonRenderer(self):
        """Test configure_logging with json_logs=True configures JSON renderer."""
        # Arrange
        with patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
             patch("src.utils.logging.structlog.configure") as mock_structlog_configure, \
             patch("src.utils.logging.structlog.processors.JSONRenderer") as mock_json_renderer:
            
            # Act
            configure_logging(json_logs=True)
            
            # Assert
            mock_json_renderer.assert_called_once()
            mock_structlog_configure.assert_called_once()
    
    def test_configure_logging_WithJsonLogsFalse_ConfiguresConsoleRenderer(self):
        """Test configure_logging with json_logs=False configures console renderer."""
        # Arrange
        with patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
             patch("src.utils.logging.structlog.configure") as mock_structlog_configure, \
             patch("src.utils.logging.structlog.dev.ConsoleRenderer") as mock_console_renderer:
            
            # Act
            configure_logging(json_logs=False)
            
            # Assert
            mock_console_renderer.assert_called_once()
            mock_structlog_configure.assert_called_once()
    
    def test_configure_logging_WithLogFile_CreatesFileHandler(self):
        """Test configure_logging with log_file creates FileHandler."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, "test.log")
            
            with patch("src.utils.logging.logging.FileHandler") as mock_file_handler, \
                 patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
                 patch("src.utils.logging.structlog.configure") as mock_structlog_configure:
                
                # Act
                configure_logging(log_file=log_file)
                
                # Assert
                mock_file_handler.assert_called_once_with(log_file)
                
                # Check that basicConfig was called with both handlers
                handlers = mock_basic_config.call_args[1]["handlers"]
                assert len(handlers) == 2  # StreamHandler and FileHandler
    
    def test_configure_logging_WithLogFileInNonExistentDir_CreatesDirectory(self):
        """Test configure_logging with log_file in non-existent directory creates the directory."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = os.path.join(tmp_dir, "logs")
            log_file = os.path.join(log_dir, "test.log")
            
            with patch("src.utils.logging.logging.FileHandler") as mock_file_handler, \
                 patch("src.utils.logging.logging.basicConfig") as mock_basic_config, \
                 patch("src.utils.logging.structlog.configure") as mock_structlog_configure:
                
                # Act
                configure_logging(log_file=log_file)
                
                # Assert
                assert os.path.exists(log_dir)
                mock_file_handler.assert_called_once_with(log_file) 