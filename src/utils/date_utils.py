"""Date utility functions for the NCAA Basketball Prediction Model.

This module provides date manipulation and formatting functions specific to NCAA
basketball data needs, including support for seasons, date ranges, and ESPN API
date format requirements.
"""

from datetime import UTC, datetime, timedelta

# Constants
SEASON_FORMAT_LENGTH = 7  # Length of a season string in format "YYYY-YY"


def get_yesterday() -> str:
    """Get yesterday's date as a string.

    Returns:
        Yesterday's date string
    """
    yesterday = datetime.now(tz=UTC) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def get_today() -> str:
    """Get today's date as a string.

    Returns:
        Today's date string
    """
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def format_date_for_api(date_str: str) -> str:
    """Convert YYYY-MM-DD date to YYYYMMDD format for API requests.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Date string in YYYYMMDD format

    Raises:
        ValueError: If date string is not in YYYY-MM-DD format
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
        return date_obj.strftime("%Y%m%d")
    except ValueError as err:
        error_msg = f"Invalid date format: {date_str}. Expected YYYY-MM-DD."
        raise ValueError(error_msg) from err


def get_date_range(start_date: str, end_date: str) -> list[str]:
    """Generate a list of dates between start_date and end_date (inclusive).

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of dates in YYYY-MM-DD format

    Raises:
        ValueError: If dates are not in YYYY-MM-DD format or if end_date is before start_date
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as err:
        error_msg = "Invalid date format. Expected YYYY-MM-DD."
        raise ValueError(error_msg) from err

    if end < start:
        error_msg = f"End date {end_date} is before start date {start_date}"
        raise ValueError(error_msg)

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def get_season_date_range(season: str) -> tuple[str, str]:
    """Convert season in YYYY-YY format to start and end dates.

    NCAA basketball season typically runs from November to April.

    Args:
        season: Season in YYYY-YY format (e.g., "2022-23")

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format

    Raises:
        ValueError: If season is not in YYYY-YY format
    """
    if not season or len(season) != SEASON_FORMAT_LENGTH or season[4] != "-":
        error_msg = f"Invalid season format: {season}. Expected YYYY-YY."
        raise ValueError(error_msg)

    try:
        start_year = int(season[0:4])
        end_year = int(f"20{season[5:7]}")
    except ValueError as err:
        error_msg = f"Invalid season format: {season}. Expected YYYY-YY."
        raise ValueError(error_msg) from err
    else:
        # NCAA basketball season typically runs from November to April
        start_date = f"{start_year}-11-01"
        end_date = f"{end_year}-04-30"

        return start_date, end_date
