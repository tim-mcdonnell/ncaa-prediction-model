import polars as pl
import pytest
from pydantic import BaseModel, Field
from typing import List, Type

from src.data.cleaning.data_cleaner import (
    DataCleaner,
    CleaningRule,
    ValidationResult,
    QualityReport
)


class PlayerTestSchema(BaseModel):
    """Test schema for player data."""
    player_id: str = Field(..., description="Unique player identifier")
    team_id: str = Field(..., description="Team identifier")
    first_name: str = Field(..., description="Player's first name")
    last_name: str = Field(..., description="Player's last name")
    jersey: int = Field(..., description="Player's jersey number", ge=0, le=99)
    position: str = Field(..., description="Player's position")
    class_year: str = Field(..., description="Player's class year (FR, SO, JR, SR)")


class TestDataCleaner:
    """Tests for the DataCleaner class."""
    
    @pytest.fixture
    def data_cleaner(self):
        """Create a DataCleaner instance for testing."""
        return DataCleaner()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for validation and cleaning."""
        return pl.DataFrame({
            "player_id": ["p1", "p2", "p3", "p4", "p5"],
            "team_id": ["t1", "t1", "t2", "t2", "t3"],
            "first_name": ["John", "Jane", "Mike", "Sarah", None],
            "last_name": ["Smith", "Doe", "Johnson", "Williams", "Brown"],
            "jersey": [23, 12, 34, -5, 101],  # -5 and 101 are invalid
            "position": ["G", "F", "C", "G", ""],  # Empty position
            "class_year": ["FR", "SO", "JR", "XYZ", "SR"]  # XYZ is invalid
        })
    
    def test_validate_schema_valid_data(self, data_cleaner, test_data):
        """Test validation with mostly valid data."""
        # Create a subset of valid data
        valid_data = test_data.filter(pl.col("player_id").is_in(["p1", "p2", "p3"]))
        
        # Run validation
        result = data_cleaner.validate_schema(valid_data, PlayerTestSchema)
        
        # Assertions
        assert result.is_valid is True
        assert len(result.validation_errors) == 0
        assert result.valid_count == 3
        assert result.invalid_count == 0
    
    def test_validate_schema_invalid_data(self, data_cleaner, test_data):
        """Test validation with invalid data."""
        # Run validation on data with issues
        result = data_cleaner.validate_schema(test_data, PlayerTestSchema)
        
        # Assertions
        assert result.is_valid is False
        assert len(result.validation_errors) > 0
        assert result.valid_count == 3  # p1, p2, and p3 are valid
        assert result.invalid_count == 2  # p4 and p5 have issues
        
        # Check specific errors
        assert any("jersey" in str(err) for err in result.validation_errors)
        assert any("first_name" in str(err) for err in result.validation_errors)
    
    def test_clean_data_with_rules(self, data_cleaner, test_data):
        """Test cleaning data with specified rules."""
        # Define cleaning rules
        rules = [
            CleaningRule(
                column="jersey",
                rule_type="clip",
                params={"min_value": 0, "max_value": 99}
            ),
            CleaningRule(
                column="position",
                rule_type="fill_empty",
                params={"fill_value": "UNKNOWN"}
            ),
            CleaningRule(
                column="first_name",
                rule_type="fill_null",
                params={"fill_value": "UNKNOWN"}
            ),
            CleaningRule(
                column="class_year",
                rule_type="map_values",
                params={"mapping": {"XYZ": "FR"}}
            )
        ]
        
        # Apply cleaning
        cleaned_data = data_cleaner.clean_data(test_data, rules)
        
        # Assertions
        assert cleaned_data.shape == test_data.shape
        
        # Check jersey numbers were clipped
        assert cleaned_data.filter(pl.col("player_id") == "p4")["jersey"][0] == 0
        assert cleaned_data.filter(pl.col("player_id") == "p5")["jersey"][0] == 99
        
        # Check empty position was filled
        assert cleaned_data.filter(pl.col("player_id") == "p5")["position"][0] == "UNKNOWN"
        
        # Check null first name was filled
        assert cleaned_data.filter(pl.col("player_id") == "p5")["first_name"][0] == "UNKNOWN"
        
        # Check invalid class year was mapped
        assert cleaned_data.filter(pl.col("player_id") == "p4")["class_year"][0] == "FR"
    
    def test_fix_common_issues(self, data_cleaner, test_data):
        """Test automatic fixing of common issues."""
        # Apply common fixes
        fixed_data = data_cleaner.fix_common_issues(test_data)
        
        # Assertions
        assert fixed_data.shape == test_data.shape
        
        # Check that some fixes were applied
        # Null values should be replaced
        assert fixed_data.filter(pl.col("player_id") == "p5")["first_name"][0] is not None
        
        # Empty strings should be replaced with NULL or default values
        assert fixed_data.filter(pl.col("player_id") == "p5")["position"][0] != ""
        
        # Number ranges should be fixed
        assert fixed_data.filter(pl.col("player_id") == "p4")["jersey"][0] >= 0
        assert fixed_data.filter(pl.col("player_id") == "p5")["jersey"][0] <= 99
    
    def test_generate_quality_report(self, data_cleaner, test_data):
        """Test generation of data quality report."""
        # Generate report
        report = data_cleaner.generate_quality_report(test_data)
        
        # Assertions
        assert isinstance(report, QualityReport)
        assert len(report.column_stats) == len(test_data.columns)
        
        # Check for specific metrics
        assert "missing_count" in report.overall_stats
        assert "total_rows" in report.overall_stats
        assert report.overall_stats["total_rows"] == len(test_data)
        
        # Check column-specific stats
        first_name_stats = next(s for s in report.column_stats if s["column"] == "first_name")
        assert first_name_stats["null_count"] == 1
        
        jersey_stats = next(s for s in report.column_stats if s["column"] == "jersey")
        assert jersey_stats["out_of_range_count"] == 2
        
        position_stats = next(s for s in report.column_stats if s["column"] == "position")
        assert position_stats["empty_count"] == 1 