from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.utils.date_utils import (
    format_date_for_api,
    get_date_range,
    get_season_date_range,
    get_today,
    get_yesterday,
)


class TestDateUtils:
    """Tests for the date utilities module."""

    @patch("src.utils.date_utils.datetime")
    def test_get_yesterday_returns_correctly_formatted_date(self, mock_datetime):
        """Test get_yesterday returns date in YYYY-MM-DD format."""
        # Arrange
        mock_now = datetime(2023, 3, 15, 12, 0, 0, tzinfo=UTC)
        mock_yesterday = datetime(2023, 3, 14, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.return_value = mock_yesterday

        # Act
        result = get_yesterday()

        # Assert
        assert result == "2023-03-14"
        mock_datetime.now.assert_called_once_with(tz=UTC)

    @patch("src.utils.date_utils.datetime")
    def test_get_today_returns_correctly_formatted_date(self, mock_datetime):
        """Test get_today returns date in YYYY-MM-DD format."""
        # Arrange
        mock_now = datetime(2023, 3, 15, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        # Act
        result = get_today()

        # Assert
        assert result == "2023-03-15"
        mock_datetime.now.assert_called_once_with(tz=UTC)

    def test_format_date_for_api_with_valid_date_returns_formatted_date(self):
        """Test format_date_for_api with valid date returns properly formatted date."""
        # Arrange
        input_date = "2023-03-15"
        expected = "20230315"

        # Act
        result = format_date_for_api(input_date)

        # Assert
        assert result == expected

    def test_format_date_for_api_with_invalid_date_raises_value_error(self):
        """Test format_date_for_api with invalid date raises ValueError."""
        # Arrange
        invalid_date = "03/15/2023"  # Not in YYYY-MM-DD format

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid date format"):
            format_date_for_api(invalid_date)

    def test_get_date_range_with_valid_dates_returns_date_list(self):
        """Test get_date_range with valid dates returns list of dates."""
        # Arrange
        start_date = "2023-03-15"
        end_date = "2023-03-17"
        expected = ["2023-03-15", "2023-03-16", "2023-03-17"]
        expected_count = 3

        # Act
        result = get_date_range(start_date, end_date)

        # Assert
        assert result == expected
        assert len(result) == expected_count

    def test_get_date_range_with_end_date_before_start_date_raises_value_error(self):
        """Test get_date_range with end date before start date raises ValueError."""
        # Arrange
        start_date = "2023-03-15"
        end_date = "2023-03-14"  # One day before start_date
        expected_error = f"End date {end_date} is before start date {start_date}"

        # Act & Assert
        with pytest.raises(ValueError, match=expected_error):
            get_date_range(start_date, end_date)

    def test_get_date_range_with_invalid_date_format_raises_value_error(self):
        """Test get_date_range with invalid date format raises ValueError."""
        # Arrange
        invalid_start = "2023/03/15"  # Incorrect format, should be YYYY-MM-DD
        valid_end = "2023-03-18"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid date format"):
            get_date_range(invalid_start, valid_end)

    def test_get_season_date_range_with_valid_season_returns_date_range(self):
        """Test get_season_date_range with valid season format returns start and end dates."""
        # Arrange
        season = "2022-23"
        expected_start = "2022-11-01"
        expected_end = "2023-04-30"

        # Act
        start, end = get_season_date_range(season)

        # Assert
        assert start == expected_start
        assert end == expected_end

    def test_get_season_date_range_with_invalid_season_format_raises_value_error(self):
        """Test get_season_date_range with invalid season format raises ValueError."""
        # Arrange
        invalid_season = "20222023"  # Invalid format, should be YYYY-YY

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid season format"):
            get_season_date_range(invalid_season)

    def test_get_date_range_returns_correct_dates(self):
        """Test get_date_range returns correct list of dates."""
        # Arrange
        start_date = "2023-03-15"
        end_date = "2023-03-17"
        expected_dates = ["2023-03-15", "2023-03-16", "2023-03-17"]
        expected_date_count = 3

        # Act
        dates = get_date_range(start_date, end_date)

        # Assert
        assert len(dates) == expected_date_count
        assert dates == expected_dates
