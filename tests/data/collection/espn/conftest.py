import json
import os

import pytest
import pytest_asyncio

from src.data.collection.espn.client import ESPNClient


@pytest.fixture
def fixture_path():
    """
    Return the path to the test fixtures directory containing ESPN API response samples.
    
    This fixture provides the absolute path to the directory where ESPN API response fixtures
    are stored. These fixtures simulate real API responses for testing without making actual
    API calls.
    
    Returns:
        str: The absolute path to the fixtures directory
    """
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "fixtures", "espn_responses")

@pytest.fixture
def load_fixture(fixture_path):
    """
    Provide a function to load fixture files from the fixtures directory.
    
    This fixture returns a function that can load and parse JSON fixture files,
    making it easy to access mock API responses in tests. The function handles
    file opening and JSON parsing.
    
    Args:
        fixture_path: Path to the fixtures directory (provided by the fixture_path fixture)
    
    Returns:
        function: A function that takes a filename and returns the parsed JSON content
    
    Example:
        def test_example(load_fixture):
            data = load_fixture("scoreboard_response.json")
            # Use the data in tests
    """
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load

@pytest_asyncio.fixture
async def espn_client():
    """
    Create a fresh ESPN client for testing with unique parameters.
    
    This fixture:
    1. Creates a new ESPNClient instance with randomized rate limit parameters
    2. Ensures each test gets an isolated client that won't interfere with other tests
    3. Properly initializes the client using an async context manager
    4. Guarantees cleanup of resources even if the test fails
    
    The randomization of rate limit parameters helps prevent test interference
    when tests are run in parallel or in different orders.
    
    Returns:
        ESPNClient: An initialized ESPN client instance ready for testing
    
    Example:
        async def test_example(espn_client):
            result = await espn_client.get_scoreboard("20230301")
            # Test with the result
    """
    # Use random-ish values to ensure tests are independent
    import random
    rate_limit = 10.0 + random.random()  # Slight randomization for uniqueness
    burst_limit = 5
    
    client = ESPNClient(rate_limit=rate_limit, burst_limit=burst_limit)
    try:
        async with client as initialized_client:
            yield initialized_client
    finally:
        # Ensure client is properly closed even if test fails
        if client._client is not None:
            await client._client.aclose() 