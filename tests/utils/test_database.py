import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.utils.database import Database

class TestDatabaseModule:
    """Tests for the database utility module."""
    
    @pytest.fixture
    def mock_duckdb_connection(self):
        """Create a mock for the DuckDB connection."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        return mock_conn
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary path for test database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.duckdb"
            yield str(db_path)
    
    def test_initialize_WithNonExistentPath_CreatesParentDirectories(self, temp_db_path, mock_duckdb_connection):
        """Test initialization creates parent directories when they don't exist."""
        # Arrange
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create a deeper non-existent path
            deep_path = os.path.join(os.path.dirname(temp_db_path), "deep", "path", "test.duckdb")
            
            # Act
            db = Database(deep_path)
            
            # Assert
            assert os.path.exists(os.path.dirname(deep_path))
            assert mock_duckdb_connection.execute.called
    
    def test_initialize_WithNoExistingTable_CreatesTable(self, temp_db_path, mock_duckdb_connection):
        """Test initialization creates the table when it doesn't exist."""
        # Arrange
        mock_duckdb_connection.execute.return_value.fetchone.return_value = None
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            
            # Assert
            create_table_call = mock_duckdb_connection.execute.call_args_list[1]
            assert "CREATE TABLE bronze_scoreboard" in create_table_call[0][0]
            
            # Verify index creation
            create_index_call = mock_duckdb_connection.execute.call_args_list[2]
            assert "CREATE INDEX" in create_index_call[0][0]
    
    def test_initialize_WithExistingTable_DoesNotRecreateTable(self, temp_db_path, mock_duckdb_connection):
        """Test initialization doesn't recreate table when it already exists."""
        # Arrange
        # Mock that the table exists
        mock_duckdb_connection.execute.return_value.fetchone.return_value = ("bronze_scoreboard",)
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            
            # Assert
            # Should only call execute once to check if table exists
            assert mock_duckdb_connection.execute.call_count == 1
            assert "SELECT name FROM sqlite_master" in mock_duckdb_connection.execute.call_args[0][0]
    
    def test_insert_bronze_scoreboard_WithNewData_InsertsCorrectly(self, temp_db_path, mock_duckdb_connection):
        """Test insertion of new data functions correctly."""
        # Arrange
        date = "2023-03-15"
        url = "https://test.api.com/scoreboard"
        params = {"dates": "20230315", "limit": 100}
        data = {"events": [{"id": "123", "name": "Test Game"}]}
        
        # Mock that record doesn't exist (no duplicate)
        mock_duckdb_connection.execute.return_value.fetchone.side_effect = [None, None]
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            db.insert_bronze_scoreboard(date, url, params, data)
            
            # Assert
            # Check the INSERT call
            insert_call = mock_duckdb_connection.execute.call_args_list[2]
            assert "INSERT INTO bronze_scoreboard" in insert_call[0][0]
            
            # The insert parameters should be [date, url, params_json, content_hash, json_data]
            insert_params = insert_call[0][1]
            assert insert_params[0] == date
            assert insert_params[1] == url
            assert json.loads(insert_params[2]) == params
            assert json.loads(insert_params[4]) == data
    
    def test_insert_bronze_scoreboard_WithDuplicateData_SkipsInsertion(self, temp_db_path, mock_duckdb_connection):
        """Test insertion of duplicate data is skipped."""
        # Arrange
        date = "2023-03-15"
        url = "https://test.api.com/scoreboard"
        params = {"dates": "20230315", "limit": 100}
        data = {"events": [{"id": "123", "name": "Test Game"}]}
        
        # Mock that record exists (is a duplicate)
        mock_duckdb_connection.execute.return_value.fetchone.side_effect = [None, (1,)]
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            db.insert_bronze_scoreboard(date, url, params, data)
            
            # Assert
            # Should not call INSERT
            call_count = mock_duckdb_connection.execute.call_count
            
            # First call checks for table existence
            # Second call checks for duplicate record
            assert call_count == 3
            
            # The duplicate check should use date and content_hash
            duplicate_check = mock_duckdb_connection.execute.call_args_list[2]
            assert "SELECT id FROM bronze_scoreboard" in duplicate_check[0][0]
            assert "WHERE date = ? AND content_hash = ?" in duplicate_check[0][0]
    
    def test_get_processed_dates_WithNoData_ReturnsEmptyList(self, temp_db_path, mock_duckdb_connection):
        """Test getting processed dates returns empty list when no data exists."""
        # Arrange
        mock_duckdb_connection.execute.return_value.fetchall.return_value = []
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            dates = db.get_processed_dates()
            
            # Assert
            assert dates == []
            assert mock_duckdb_connection.execute.call_args_list[-1][0][0].strip().startswith("SELECT DISTINCT date")
    
    def test_get_processed_dates_WithExistingData_ReturnsDatesList(self, temp_db_path, mock_duckdb_connection):
        """Test getting processed dates returns correct list when data exists."""
        # Arrange
        mock_duckdb_connection.execute.return_value.fetchall.return_value = [
            ("2023-03-15",),
            ("2023-03-16",),
            ("2023-03-17",),
        ]
        
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            dates = db.get_processed_dates()
            
            # Assert
            assert dates == ["2023-03-15", "2023-03-16", "2023-03-17"]
    
    def test_close_WhenCalled_ClosesConnection(self, temp_db_path, mock_duckdb_connection):
        """Test close method properly closes the database connection."""
        # Arrange
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            db = Database(temp_db_path)
            db.close()
            
            # Assert
            mock_duckdb_connection.close.assert_called_once()
    
    def test_context_manager_WhenUsed_ClosesConnectionAfter(self, temp_db_path, mock_duckdb_connection):
        """Test context manager properly closes connection when exiting context."""
        # Arrange
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            with Database(temp_db_path) as db:
                pass
            
            # Assert
            mock_duckdb_connection.close.assert_called_once() 