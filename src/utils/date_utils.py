from datetime import datetime, timedelta
from typing import List, Optional, Tuple

def get_yesterday() -> str:
    """
    Get yesterday's date in YYYY-MM-DD format.
    
    Returns:
        Yesterday's date string
    """
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

def get_today() -> str:
    """
    Get today's date in YYYY-MM-DD format.
    
    Returns:
        Today's date string
    """
    return datetime.now().strftime("%Y-%m-%d")

def format_date_for_espn(date_str: str) -> str:
    """
    Convert YYYY-MM-DD date format to YYYYMMDD for ESPN API.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Date in YYYYMMDD format
        
    Raises:
        ValueError: If date_str is not in YYYY-MM-DD format
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")

def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Generate list of dates between start_date and end_date (inclusive).
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of dates in YYYY-MM-DD format
        
    Raises:
        ValueError: If dates are invalid or end_date is before start_date
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD.")
    
    if end < start:
        raise ValueError(f"End date {end_date} is before start date {start_date}")
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates

def get_season_date_range(season: str) -> Tuple[str, str]:
    """
    Convert season in YYYY-YY format to start and end dates.
    NCAA basketball season typically runs from November to April.
    
    Args:
        season: Season in YYYY-YY format (e.g., "2022-23")
        
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
        
    Raises:
        ValueError: If season is not in YYYY-YY format
    """
    if not season or len(season) != 7 or season[4] != '-':
        raise ValueError(f"Invalid season format: {season}. Expected YYYY-YY.")
    
    try:
        start_year = int(season[0:4])
        end_year = int(f"20{season[5:7]}")
        
        # NCAA basketball season typically starts in November
        start_date = f"{start_year}-11-01"
        
        # Season ends in April of the next year
        end_date = f"{end_year}-04-30"
        
        return start_date, end_date
    except ValueError:
        raise ValueError(f"Invalid season format: {season}. Expected YYYY-YY.") 