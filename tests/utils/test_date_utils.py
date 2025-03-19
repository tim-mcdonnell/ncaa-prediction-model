import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.utils.date_utils import (
    get_yesterday,
    get_today,
    format_date_for_espn,
    generate_date_range,
    get_season_date_range
)

class TestDateUtilsModule:
    """Tests for the date utilities module."""
    
    def test_get_yesterday_WhenCalled_ReturnsCorrectDateFormat(self):
        """Test get_yesterday returns date in YYYY-MM-DD format."""
        # Arrange
        fixed_date = datetime(2023, 3, 15)
        expected_yesterday = "2023-03-14"
        
        # Act
        with patch("src.utils.date_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            result = get_yesterday()
            
        # Assert
        assert result == expected_yesterday
    
    def test_get_today_WhenCalled_ReturnsCorrectDateFormat(self):
        """Test get_today returns date in YYYY-MM-DD format."""
        # Arrange
        fixed_date = datetime(2023, 3, 15)
        expected_today = "2023-03-15"
        
        # Act
        with patch("src.utils.date_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            result = get_today()
            
        # Assert
        assert result == expected_today
    
    def test_format_date_for_espn_WithValidDate_ReturnsFormattedDate(self):
        """Test format_date_for_espn with valid date returns YYYYMMDD format."""
        # Arrange
        test_date = "2023-03-15"
        expected_formatted = "20230315"
        
        # Act
        result = format_date_for_espn(test_date)
        
        # Assert
        assert result == expected_formatted
    
    def test_format_date_for_espn_WithInvalidDate_RaisesValueError(self):
        """Test format_date_for_espn with invalid date raises ValueError."""
        # Arrange
        invalid_dates = ["2023/03/15", "03-15-2023", "invalid_date"]
        
        # Act & Assert
        for invalid_date in invalid_dates:
            with pytest.raises(ValueError):
                format_date_for_espn(invalid_date)
    
    def test_generate_date_range_WithValidDates_ReturnsCorrectRange(self):
        """Test generate_date_range with valid dates returns the correct date range."""
        # Arrange
        start_date = "2023-03-15"
        end_date = "2023-03-18"
        expected_range = ["2023-03-15", "2023-03-16", "2023-03-17", "2023-03-18"]
        
        # Act
        result = generate_date_range(start_date, end_date)
        
        # Assert
        assert result == expected_range
        assert len(result) == 4
    
    def test_generate_date_range_WithSameStartAndEndDate_ReturnsSingleDateList(self):
        """Test generate_date_range with same start and end date returns a list with single date."""
        # Arrange
        date = "2023-03-15"
        
        # Act
        result = generate_date_range(date, date)
        
        # Assert
        assert result == [date]
        assert len(result) == 1
    
    def test_generate_date_range_WithEndDateBeforeStartDate_RaisesValueError(self):
        """Test generate_date_range with end date before start date raises ValueError."""
        # Arrange
        start_date = "2023-03-15"
        end_date = "2023-03-14"
        
        # Act & Assert
        with pytest.raises(ValueError):
            generate_date_range(start_date, end_date)
    
    def test_generate_date_range_WithInvalidDateFormat_RaisesValueError(self):
        """Test generate_date_range with invalid date format raises ValueError."""
        # Arrange
        invalid_dates = [
            ("2023/03/15", "2023-03-18"),
            ("2023-03-15", "invalid_date"),
            ("invalid_date", "invalid_date"),
        ]
        
        # Act & Assert
        for start, end in invalid_dates:
            with pytest.raises(ValueError):
                generate_date_range(start, end)
    
    def test_get_season_date_range_WithValidSeason_ReturnsCorrectDateRange(self):
        """Test get_season_date_range with valid season returns correct start and end dates."""
        # Arrange
        season = "2022-23"
        expected_start = "2022-11-01"
        expected_end = "2023-04-30"
        
        # Act
        start_date, end_date = get_season_date_range(season)
        
        # Assert
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_get_season_date_range_WithInvalidSeason_RaisesValueError(self):
        """Test get_season_date_range with invalid season format raises ValueError."""
        # Arrange
        invalid_seasons = ["2022", "2022-2023", "22-23", "", None]
        
        # Act & Assert
        for invalid_season in invalid_seasons:
            with pytest.raises(ValueError):
                get_season_date_range(invalid_season) 