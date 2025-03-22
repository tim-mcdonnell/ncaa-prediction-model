import json
import os
import shutil
from pathlib import Path

import polars as pl
import pytest

from src.utils.config import ESPNApiConfig, RequestSettings
from src.utils.database import Database
from src.utils.parquet_storage import ParquetStorage


class TestParquetIntegration:
    """Integration tests for the Parquet storage implementation."""

    @pytest.fixture()
    def test_config_path(self):
        """Path to test configuration."""
        return os.path.join("tests", "data", "config_test.json")

    @pytest.fixture()
    def test_data_dir(self):
        """Create a temporary directory for test data."""
        data_dir = Path(os.path.join("tests", "data", "integration_test"))
        data_dir.mkdir(parents=True, exist_ok=True)

        try:
            yield str(data_dir)
        finally:
            if data_dir.exists():
                try:
                    shutil.rmtree(data_dir)
                except (PermissionError, OSError):
                    pass

    @pytest.fixture()
    def espn_api_config(self):
        """Return ESPN API configuration for testing."""
        # Create RequestSettings object
        request_settings = RequestSettings(
            initial_request_delay=0.1,
            max_retries=1,
            timeout=5,
            batch_size=2,
            max_concurrency=1,
        )

        # Create ESPNApiConfig with request_settings
        config = ESPNApiConfig(
            base_url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
            endpoints={"scoreboard": "scoreboard"},
            request_settings=request_settings,
        )

        # Add historical_start_date as an attribute for testing
        config.historical_start_date = "2023-03-01"

        return config

    @pytest.fixture()
    def mock_ingest_config(self, espn_api_config, test_data_dir):
        """Create test ingestion configuration."""
        from src.ingest.scoreboard import ScoreboardIngestionConfig

        # Use local test data directory
        raw_dir = os.path.join(test_data_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        # Configure for specific dates to test partitioning
        return ScoreboardIngestionConfig(
            espn_api_config=espn_api_config,
            date="2023-03-15",  # Specific date for consistent testing
            parquet_dir=raw_dir,
            force_overwrite=True,
        )

    @pytest.mark.asyncio()
    async def test_ingestion_to_new_structure(self, mock_ingest_config, monkeypatch):
        """Test that data is correctly ingested to the partitioned Parquet structure."""
        # Arrange
        from src.ingest.scoreboard import ingest_scoreboard_async

        # Mock the API response
        async def mock_fetch_scoreboard_async(*args, **kwargs):
            return {
                "events": [
                    {
                        "id": "401403389",
                        "date": "2023-03-15T23:30Z",
                        "name": "Test Game",
                        "competitions": [
                            {
                                "id": "401403389",
                                "status": {"type": {"completed": True}},
                                "competitors": [
                                    {"team": {"id": "52", "score": "75"}},
                                    {"team": {"id": "2", "score": "70"}},
                                ],
                            }
                        ],
                    }
                ]
            }

        # Apply monkey patches
        monkeypatch.setattr(
            "src.utils.espn_api_client.ESPNApiClient.fetch_scoreboard_async",
            mock_fetch_scoreboard_async,
        )

        # Act
        await ingest_scoreboard_async(mock_ingest_config)

        # Assert
        # Check that data was written to the correct partition
        parquet_dir = mock_ingest_config.parquet_dir
        year_month_path = os.path.join(parquet_dir, "scoreboard", "year=2023", "month=03")

        # Verify the directory structure was created
        assert os.path.exists(year_month_path), "Year/month partition directory not created"

        # Get the Parquet files in the partition
        parquet_files = list(Path(year_month_path).glob("*.parquet"))
        assert len(parquet_files) > 0, "No Parquet files were created"

        # Read the Parquet file and verify content - using polars directly to avoid schema conflicts
        data = pl.read_parquet(parquet_files[0])
        assert len(data) > 0, "Parquet file contains no data"

        # Verify the expected fields and partitioning
        assert "date" in data.columns, "date column missing"
        assert "raw_data" in data.columns, "raw_data column missing"
        assert "year" in data.columns, "year partition column missing"
        assert "month" in data.columns, "month partition column missing"

        # Check the data values
        assert "2023-03-15" in data["date"].to_list(), "Date not found in Parquet data"
        assert all(data["year"] == "2023"), "Year partition value incorrect"
        assert all(data["month"] == "03"), "Month partition value incorrect"

        # Check that at least one record contains the expected game ID in the raw data
        game_found = False
        for raw_data in data["raw_data"]:
            if "401403389" in raw_data:
                game_found = True
                break
        assert game_found, "Game ID not found in Parquet data"

    def test_bronze_to_silver_process_with_new_structure(self, mock_ingest_config, monkeypatch):
        """Test that data can be read from Parquet files for silver processing."""
        # Arrange - Create test Parquet data
        parquet_dir = mock_ingest_config.parquet_dir
        scoreboard_dir = os.path.join(parquet_dir, "scoreboard", "year=2023", "month=03")
        os.makedirs(scoreboard_dir, exist_ok=True)

        # Create sample data
        test_data = pl.DataFrame(
            {
                "id": [1],
                "date": ["2023-03-15"],
                "source_url": [
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
                ],
                "parameters": [json.dumps({"date": "20230315"})],
                "content_hash": ["hash1"],
                "raw_data": [
                    json.dumps(
                        {
                            "events": [
                                {
                                    "id": "401403389",
                                    "date": "2023-03-15T23:30Z",
                                    "name": "Test Game",
                                    "competitions": [
                                        {
                                            "id": "401403389",
                                            "status": {"type": {"completed": True}},
                                            "competitors": [
                                                {"team": {"id": "52", "score": "75"}},
                                                {"team": {"id": "2", "score": "70"}},
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    )
                ],
                "created_at": ["2023-03-15T12:00:00"],
                "year": ["2023"],
                "month": ["03"],
            }
        )

        # Write test Parquet file
        test_file = os.path.join(scoreboard_dir, "data.parquet")
        test_data.write_parquet(test_file)

        # Create a ParquetStorage instance
        storage = ParquetStorage(base_dir=parquet_dir)

        # Act - Read the data using ParquetStorage
        scoreboard_data = storage.read_scoreboard_data(date="2023-03-15")

        # Assert
        # Check that data was read correctly
        assert scoreboard_data is not None, "No data returned from ParquetStorage"

        # Parse JSON to verify content
        parsed_data = json.loads(scoreboard_data)
        assert "events" in parsed_data, "events not found in data"
        assert len(parsed_data["events"]) > 0, "No events found in data"
        assert parsed_data["events"][0]["id"] == "401403389", "Game ID mismatch"

    def test_historical_queries_return_same_results(
        self, mock_ingest_config, monkeypatch, test_data_dir
    ):
        """Test that historical queries return the same results with the new structure."""
        # Arrange - Set up both DuckDB and Parquet storage
        db_path = os.path.join(test_data_dir, "test.duckdb")
        parquet_dir = os.path.join(test_data_dir, "raw")

        # Create test data in DuckDB
        conn = Database(db_path)

        # Insert test data into DuckDB
        conn.insert_bronze_scoreboard(
            date="2023-03-15",
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
            params={"date": "20230315"},
            data={
                "events": [
                    {
                        "id": "401403389",
                        "date": "2023-03-15T23:30Z",
                        "name": "Test Game",
                        "competitions": [
                            {
                                "id": "401403389",
                                "status": {"type": {"completed": True}},
                                "competitors": [
                                    {"team": {"id": "52", "score": "75"}},
                                    {"team": {"id": "2", "score": "70"}},
                                ],
                            }
                        ],
                    }
                ]
            },
        )

        # Create the same data in Parquet
        scoreboard_dir = os.path.join(parquet_dir, "scoreboard", "year=2023", "month=03")
        os.makedirs(scoreboard_dir, exist_ok=True)

        test_data = pl.DataFrame(
            {
                "id": [1],
                "date": ["2023-03-15"],
                "source_url": [
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
                ],
                "parameters": [json.dumps({"date": "20230315"})],
                "content_hash": ["hash1"],
                "raw_data": [
                    json.dumps(
                        {
                            "events": [
                                {
                                    "id": "401403389",
                                    "date": "2023-03-15T23:30Z",
                                    "name": "Test Game",
                                    "competitions": [
                                        {
                                            "id": "401403389",
                                            "status": {"type": {"completed": True}},
                                            "competitors": [
                                                {"team": {"id": "52", "score": "75"}},
                                                {"team": {"id": "2", "score": "70"}},
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    )
                ],
                "created_at": ["2023-03-15T12:00:00"],
                "year": ["2023"],
                "month": ["03"],
            }
        )

        # Write test Parquet file
        test_file = os.path.join(scoreboard_dir, "data.parquet")
        test_data.write_parquet(test_file)

        # Create storage instance
        parquet_storage = ParquetStorage(base_dir=parquet_dir)

        # Act - Get data from both sources
        # Query DuckDB
        result_duckdb = conn.conn.execute(
            "SELECT raw_data FROM bronze_scoreboard WHERE date = '2023-03-15'"
        ).fetchone()
        db_data = json.loads(result_duckdb[0]) if result_duckdb else None

        # Query Parquet
        parquet_data_raw = parquet_storage.read_scoreboard_data(date="2023-03-15")
        parquet_data = json.loads(parquet_data_raw) if parquet_data_raw else None

        # Assert
        # Both data sources should return data
        assert db_data is not None, "No data returned from DuckDB"
        assert parquet_data is not None, "No data returned from Parquet"

        # Data should be identical
        assert "events" in db_data, "events not found in DuckDB data"
        assert "events" in parquet_data, "events not found in Parquet data"

        # Compare specific fields
        assert db_data["events"][0]["id"] == parquet_data["events"][0]["id"], "Game ID mismatch"
        assert db_data["events"][0]["date"] == parquet_data["events"][0]["date"], "Date mismatch"

        # Clean up
        conn.close()

    def test_record_counts_match_between_old_and_new(self, mock_ingest_config, test_data_dir):
        """Test that record counts match between DuckDB and Parquet storage."""
        # Arrange - Set up both DuckDB and Parquet storage
        db_path = os.path.join(test_data_dir, "test.duckdb")
        parquet_dir = os.path.join(test_data_dir, "raw")

        # Create test data in DuckDB
        conn = Database(db_path)

        # Insert multiple test records
        for day in range(15, 18):  # 15, 16, 17
            conn.insert_bronze_scoreboard(
                date=f"2023-03-{day:02d}",
                url="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
                params={"date": f"202303{day:02d}"},
                data={
                    "events": [
                        {
                            "id": f"4014033{day:02d}",
                            "date": f"2023-03-{day:02d}T23:30Z",
                            "name": f"Test Game {day}",
                        }
                    ]
                },
            )

        # Create the same data in Parquet
        scoreboard_dir = os.path.join(parquet_dir, "scoreboard", "year=2023", "month=03")
        os.makedirs(scoreboard_dir, exist_ok=True)

        test_data = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "date": ["2023-03-15", "2023-03-16", "2023-03-17"],
                "source_url": [
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
                ]
                * 3,
                "parameters": [
                    json.dumps({"date": "20230315"}),
                    json.dumps({"date": "20230316"}),
                    json.dumps({"date": "20230317"}),
                ],
                "content_hash": ["hash1", "hash2", "hash3"],
                "raw_data": [
                    json.dumps(
                        {
                            "events": [
                                {
                                    "id": "40140315",
                                    "date": "2023-03-15T23:30Z",
                                    "name": "Test Game 15",
                                }
                            ]
                        }
                    ),
                    json.dumps(
                        {
                            "events": [
                                {
                                    "id": "40140316",
                                    "date": "2023-03-16T23:30Z",
                                    "name": "Test Game 16",
                                }
                            ]
                        }
                    ),
                    json.dumps(
                        {
                            "events": [
                                {
                                    "id": "40140317",
                                    "date": "2023-03-17T23:30Z",
                                    "name": "Test Game 17",
                                }
                            ]
                        }
                    ),
                ],
                "created_at": [
                    "2023-03-15T12:00:00",
                    "2023-03-16T12:00:00",
                    "2023-03-17T12:00:00",
                ],
                "year": ["2023"] * 3,
                "month": ["03"] * 3,
            }
        )

        # Write test Parquet file
        test_file = os.path.join(scoreboard_dir, "data.parquet")
        test_data.write_parquet(test_file)

        # Act
        # Count records in DuckDB
        duckdb_count = conn.conn.execute("SELECT COUNT(*) FROM bronze_scoreboard").fetchone()[0]

        # Count records in Parquet using polars to avoid schema issues
        parquet_files = list(Path(parquet_dir).glob("**/scoreboard/**/*.parquet"))
        parquet_count = sum(len(pl.read_parquet(file)) for file in parquet_files)

        # Assert
        assert duckdb_count == 3, f"Expected 3 records in DuckDB, got {duckdb_count}"
        assert parquet_count == 3, f"Expected 3 records in Parquet, got {parquet_count}"
        assert duckdb_count == parquet_count, "Record counts don't match between DuckDB and Parquet"

        # Clean up
        conn.close()
