"""
Configuration settings for the NCAA prediction model.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Data paths
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# API configuration
ESPN_API_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"

# Define the seasons to analyze (e.g., "2000-01" to "2022-23")
SEASONS = [f"{year}-{str(year+1)[-2:]}" for year in range(2000, 2023)]

# Model configuration
RANDOM_SEED = 42
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.2

# Dashboard configuration
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8050)) 