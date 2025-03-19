import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.database import Database


class TestDatabaseModule:
    """Tests for the database module."""

    @pytest.fixture()
    def sample_scoreboard_data(self):
        """Create sample scoreboard data for testing."""
        return {
            "leagues": [{"id": "mens-college-basketball"}],
            "events": [
                {
                    "id": "401403389",
                    "date": "2023-03-15T23:30Z",
                    "name": "Team A vs Team B",
                    "competitions": [
                        {
                            "id": "401403389",
                            "competitors": [
                                {"id": "TeamA", "score": "75", "homeAway": "home"},
                                {"id": "TeamB", "score": "70", "homeAway": "away"},
                            ],
                        }
                    ],
                }
            ],
        }

    @pytest.fixture()
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        db_path = Path(
            os.path.join(os.path.dirname(__file__), f"temp_test_db_{os.getpid()}.duckdb")
        )
        try:
            yield str(db_path)
        finally:
            if db_path.exists():
                os.remove(db_path)

    def test_initialize_with_non_existent_path_creates_parent_directories(
        self,
        temp_db_path,
    ):
        """Test initializing the database with a non-existent path creates parent directories."""
        # Arrange
        parent_dir = os.path.dirname(temp_db_path)
        deep_path = os.path.join(parent_dir, "deep", "nested", "db.duckdb")
        deep_dir = os.path.dirname(deep_path)

        with patch("src.utils.database.duckdb.connect") as mock_duckdb_connect:
            mock_duckdb_connection = MagicMock()
            mock_duckdb_connect.return_value = mock_duckdb_connection

            # Act
            _ = Database(deep_path)  # Using _ to explicitly show variable is unused

            # Assert
            assert os.path.exists(deep_dir)
            assert mock_duckdb_connect.called
            assert mock_duckdb_connection.execute.called

    def test_initialize_with_no_existing_table_creates_table(
        self,
        temp_db_path,
    ):
        """Test initializing the database with no existing table creates it."""
        # Arrange
        mock_duckdb_connection = MagicMock()

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            _ = Database(temp_db_path)  # Using _ to explicitly show variable is unused

            # Assert
            # Check that correct SQL statements were executed
            execute_calls = mock_duckdb_connection.execute.call_args_list
            create_table_found = False

            for call in execute_calls:
                sql = call[0][0]
                if "CREATE TABLE IF NOT EXISTS bronze_scoreboard" in sql:
                    create_table_found = True
                    break

            assert create_table_found, "CREATE TABLE call not found"

    def test_initialize_with_existing_table_does_not_recreate_table(
        self,
        temp_db_path,
    ):
        """Test initializing the database with an existing table doesn't recreate it."""
        # Arrange
        mock_duckdb_connection = MagicMock()
        # Simulate table already exists
        mock_duckdb_connection.execute.return_value.fetchall.return_value = [("bronze_scoreboard",)]

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            _ = Database(temp_db_path)  # Using _ to explicitly show variable is unused

            # Assert
            # Should still try to create table (IF NOT EXISTS)
            execute_calls = mock_duckdb_connection.execute.call_args_list
            create_table_found = False

            for call in execute_calls:
                sql = call[0][0]
                if "CREATE TABLE IF NOT EXISTS bronze_scoreboard" in sql:
                    create_table_found = True
                    break

            assert create_table_found, "CREATE TABLE IF NOT EXISTS should still be called"

    def test_insert_bronze_scoreboard_with_new_data_inserts_correctly(
        self,
        temp_db_path,
        sample_scoreboard_data,
    ):
        """Test inserting new scoreboard data works correctly."""
        # Arrange
        test_date = "2023-03-15"
        test_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
        test_params = {"dates": "20230315", "limit": "300", "groups": "50"}

        mock_duckdb_connection = MagicMock()
        # Make get_processed_dates return empty list (no existing data)
        mock_duckdb_connection.execute.return_value.fetchall.return_value = []

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create database instance
            db = Database(temp_db_path)

            # Act
            db.insert_bronze_scoreboard(
                date=test_date,
                url=test_url,
                params=test_params,
                data=sample_scoreboard_data,
            )

            # Assert
            # Check that the SQL insert was called
            execute_calls = mock_duckdb_connection.execute.call_args_list
            # Use any() with generator expression instead of list comprehension to avoid long line
            has_insert = any(
                "INSERT INTO bronze_scoreboard" in call[0][0] for call in execute_calls
            )
            assert has_insert, "INSERT INTO call not found"

            # Check correct data was inserted
            # The second parameter to execute is the data tuple
            insert_call = next(
                call for call in execute_calls if "INSERT INTO bronze_scoreboard" in call[0][0]
            )
            inserted_data = insert_call[0][1]
            assert inserted_data[0] == test_date
            assert inserted_data[1] == test_url
            assert inserted_data[2] == json.dumps(test_params)
            assert inserted_data[3] == json.dumps(sample_scoreboard_data)

    def test_insert_bronze_scoreboard_with_duplicate_data_skips_insertion(
        self,
        temp_db_path,
        sample_scoreboard_data,
    ):
        """Test that inserting duplicate data skips the insertion."""
        # Arrange
        test_date = "2023-03-15"
        test_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
        test_params = {"dates": "20230315", "limit": "300", "groups": "50"}

        mock_duckdb_connection = MagicMock()
        # Simulate data already exists
        mock_duckdb_connection.execute.return_value.fetchall.return_value = [
            (test_date,)
        ]  # Processed dates includes test_date

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create database instance
            db = Database(temp_db_path)

            # Act
            db.insert_bronze_scoreboard(
                date=test_date,
                url=test_url,
                params=test_params,
                data=sample_scoreboard_data,
            )

            # Assert
            # Check that the SQL insert was not called
            execute_calls = mock_duckdb_connection.execute.call_args_list
            # Use any() with generator expression instead of list comprehension to avoid long line
            has_insert = any(
                "INSERT INTO bronze_scoreboard" in call[0][0] for call in execute_calls
            )
            assert not has_insert, "No INSERT should be called for duplicate data"

    def test_get_processed_dates_with_no_data_returns_empty_list(
        self,
        temp_db_path,
    ):
        """Test that get_processed_dates returns an empty list when no data exists."""
        # Arrange
        mock_duckdb_connection = MagicMock()
        # Simulate no data
        mock_duckdb_connection.execute.return_value.fetchall.return_value = []

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create database instance
            db = Database(temp_db_path)

            # Act
            dates = db.get_processed_dates()

            # Assert
            assert dates == []
            mock_duckdb_connection.execute.assert_called_with(
                "SELECT DISTINCT date FROM bronze_scoreboard ORDER BY date"
            )

    def test_get_processed_dates_with_existing_data_returns_dates_list(
        self,
        temp_db_path,
    ):
        """Test that get_processed_dates returns a list of dates when data exists."""
        # Arrange
        mock_duckdb_connection = MagicMock()
        # Simulate existing data
        mock_duckdb_connection.execute.return_value.fetchall.return_value = [
            ("2023-03-15",),
            ("2023-03-16",),
            ("2023-03-17",),
        ]

        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create database instance
            db = Database(temp_db_path)

            # Act
            dates = db.get_processed_dates()

            # Assert
            assert dates == ["2023-03-15", "2023-03-16", "2023-03-17"]

    def test_close_when_called_closes_connection(self, temp_db_path, mock_duckdb_connection):
        """Test close method properly closes the database connection."""
        # Arrange
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Create database instance
            db = Database(temp_db_path)

            # Act
            db.close()

            # Assert
            mock_duckdb_connection.close.assert_called_once()

    def test_context_manager_when_used_closes_connection_after(
        self,
        temp_db_path,
        mock_duckdb_connection,
    ):
        """Test context manager properly closes the connection after use."""
        # Arrange
        with patch("src.utils.database.duckdb.connect", return_value=mock_duckdb_connection):
            # Act
            with Database(temp_db_path) as _:  # Using _ to explicitly show variable is unused
                pass

            # Assert
            mock_duckdb_connection.close.assert_called_once()

    @pytest.fixture()
    def mock_duckdb_connection(self):
        """Create a mock DuckDB connection for testing."""
        connection = MagicMock()
        return connection
