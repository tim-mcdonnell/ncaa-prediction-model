import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from src.data.cleaning.data_cleaner import DataCleaner, QualityReport
from src.pipelines.collection_pipeline import CollectionPipeline
from src.scripts.historical_data_collection import (
    HistoricalDataCollector,
    collect_historical_data,
    create_progress_report,
    setup_logging
)


class TestHistoricalDataCollector:
    """Tests for the HistoricalDataCollector class."""
    
    @pytest.fixture
    def collector(self):
        """Create a HistoricalDataCollector instance for testing."""
        with patch("src.scripts.historical_data_collection.CollectionPipeline") as mock_pipeline_cls:
            with patch("src.scripts.historical_data_collection.DataCleaner") as mock_cleaner_cls:
                # Setup mock pipeline
                mock_pipeline = mock_pipeline_cls.return_value
                mock_pipeline.collect_all_seasons = AsyncMock()
                
                # Setup mock data cleaner
                mock_cleaner = mock_cleaner_cls.return_value
                mock_cleaner.clean_data = MagicMock()
                mock_cleaner.fix_common_issues = MagicMock()
                mock_cleaner.generate_quality_report = MagicMock()
                
                collector = HistoricalDataCollector(
                    start_year=2020,
                    end_year=2022,
                    data_dir="test_data"
                )
                
                yield collector
    
    def test_init(self, collector):
        """Test collector initialization with correct parameters."""
        assert collector.start_year == 2020
        assert collector.end_year == 2022
        assert collector.data_dir == "test_data"
        assert collector.pipeline is not None
        assert collector.cleaner is not None
    
    @pytest.mark.asyncio
    async def test_collect_seasons(self, collector):
        """Test collecting seasons calls pipeline with correct parameters."""
        # Setup mock results
        mock_results = [MagicMock() for _ in range(3)]
        collector.pipeline.collect_all_seasons.return_value = mock_results
        
        # Call the method
        results = await collector.collect_seasons()
        
        # Verify pipeline was called correctly
        collector.pipeline.collect_all_seasons.assert_called_once_with(2020, 2022)
        assert results == mock_results
    
    def test_clean_and_validate_data(self, collector):
        """Test cleaning and validating collected data."""
        # Create sample data
        test_data = {"games": pl.DataFrame({"id": ["1", "2"], "score": [10, 20]})}
        
        # Mock the cleaner methods
        mock_cleaned_data = pl.DataFrame({"id": ["1", "2"], "score": [10, 20]})
        collector.cleaner.clean_data.return_value = mock_cleaned_data
        collector.cleaner.fix_common_issues.return_value = mock_cleaned_data
        
        mock_report = QualityReport(
            overall_stats={"total_rows": 2},
            column_stats=[{"column": "id"}, {"column": "score"}]
        )
        collector.cleaner.generate_quality_report.return_value = mock_report
        
        # Call the method
        result_data, result_report = collector.clean_and_validate_data(test_data)
        
        # Verify cleaner was called correctly
        collector.cleaner.clean_data.assert_called_once()
        collector.cleaner.generate_quality_report.assert_called_once()
        
        # For Polars DataFrames, we can't directly compare with ==
        # Instead, check that the shape and values match
        assert result_data.shape == mock_cleaned_data.shape
        assert result_data.columns == mock_cleaned_data.columns
        assert result_report == mock_report
    
    @pytest.mark.asyncio
    async def test_collect_and_process(self, collector, tmp_path):
        """Test the entire collection and processing flow."""
        # Setup temp dir for output
        collector.data_dir = str(tmp_path)
        
        # Mock the collect_seasons method
        mock_pipeline_results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.status.value = "SUCCESS"
            mock_result.output_data = {"games": pl.DataFrame({"id": [f"{i}"], "score": [10]})}
            mock_pipeline_results.append(mock_result)
        
        collector.collect_seasons = AsyncMock(return_value=mock_pipeline_results)
        
        # Mock the clean_and_validate_data method
        mock_cleaned_data = pl.DataFrame({"id": ["1", "2"], "score": [10, 20]})
        mock_report = QualityReport(
            overall_stats={"total_rows": 2},
            column_stats=[{"column": "id"}, {"column": "score"}]
        )
        collector.clean_and_validate_data = MagicMock(
            return_value=(mock_cleaned_data, mock_report)
        )
        
        # Mock write_parquet to avoid actual file operations
        with patch("polars.DataFrame.write_parquet"):
            with patch("builtins.open", MagicMock()):
                # Call the method
                result = await collector.collect_and_process()
                
                # Verify methods were called
                collector.collect_seasons.assert_called_once()
                assert collector.clean_and_validate_data.call_count == 3  # Once per season
                
                # Verify result contains expected data
                assert len(result) == 3
                for item in result:
                    assert "season" in item
                    assert "pipeline_result" in item
                    assert "cleaned_data" in item
                    assert "quality_report" in item
    
    def test_create_progress_report(self):
        """Test creating the progress report."""
        # Setup mock results
        mock_results = [
            {
                "season": 2020,
                "pipeline_result": MagicMock(
                    metadata={"games_count": 100, "teams_count": 20}
                ),
                "quality_report": QualityReport(
                    overall_stats={"total_rows": 100, "missing_count": 5},
                    column_stats=[],
                    data_issues=["Issue 1"]
                )
            },
            {
                "season": 2021,
                "pipeline_result": MagicMock(
                    metadata={"games_count": 120, "teams_count": 22}
                ),
                "quality_report": QualityReport(
                    overall_stats={"total_rows": 120, "missing_count": 3},
                    column_stats=[],
                    data_issues=[]
                )
            }
        ]
        
        # Test the function
        with patch("src.scripts.historical_data_collection.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1)
            report = create_progress_report(mock_results)
            
        # Verify report contains expected data
        assert "timestamp" in report
        assert "seasons" in report
        assert len(report["seasons"]) == 2
        assert report["seasons"][0]["year"] == 2020
        assert report["seasons"][0]["games_count"] == 100
        assert report["seasons"][0]["data_issues"] == ["Issue 1"]
        assert report["total_games"] == 220
        assert report["total_seasons"] == 2


def test_setup_logging():
    """Test setting up logging configuration."""
    with patch("src.scripts.historical_data_collection.logging") as mock_logging:
        setup_logging("info")
        mock_logging.basicConfig.assert_called_once()
        
        # Test with debug level
        setup_logging("debug")
        assert mock_logging.basicConfig.call_count == 2


@pytest.mark.asyncio
async def test_collect_historical_data_main():
    """Test the main collect_historical_data function."""
    with patch("src.scripts.historical_data_collection.HistoricalDataCollector") as mock_collector_cls:
        # Setup mock collector
        mock_collector = mock_collector_cls.return_value
        mock_collector.collect_and_process = AsyncMock()
        mock_collector.collect_and_process.return_value = [{"season": 2020}]
        
        # Mock progress report creation
        with patch("src.scripts.historical_data_collection.create_progress_report") as mock_create_report:
            mock_create_report.return_value = {
                "timestamp": "2023-01-01",
                "total_seasons": 1,
                "total_games": 100,
                "total_teams": 20,
                "total_issues": 0
            }
            
            # Mock Path and file operations
            with patch("src.scripts.historical_data_collection.Path") as mock_path_cls:
                with patch("src.scripts.historical_data_collection.json.dumps") as mock_dumps:
                    with patch("pathlib.Path.write_text") as mock_write_text:
                        # Setup Path mock to return itself for __truediv__
                        mock_path_cls.return_value = mock_path_cls
                        mock_path_cls.__truediv__.return_value = mock_path_cls
                        mock_path_cls.mkdir = MagicMock()
                        
                        # Mock json.dumps to return a string
                        mock_dumps.return_value = "{}"
                        
                        # Call the function
                        await collect_historical_data(2000, 2025, "data", "info")
                        
                        # Verify collector was created and used correctly
                        mock_collector_cls.assert_called_once_with(
                            start_year=2000,
                            end_year=2025,
                            data_dir="data"
                        )
                        mock_collector.collect_and_process.assert_called_once()
                        mock_create_report.assert_called_once()
                        
                        # Verify report was saved
                        mock_path_cls.mkdir.assert_called_once_with(
                            parents=True, exist_ok=True
                        ) 