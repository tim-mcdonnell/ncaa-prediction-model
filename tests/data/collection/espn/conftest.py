import json
import os

import pytest
import pytest_asyncio

from src.data.collection.espn.client import ESPNClient


@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file from the fixtures directory."""
    def _load(filename):
        with open(os.path.join(fixture_path, filename), "r") as f:
            return json.load(f)
    return _load

@pytest_asyncio.fixture
async def espn_client():
    """Create an ESPN client for testing."""
    client = ESPNClient(rate_limit=10.0, burst_limit=5)
    async with client as initialized_client:
        yield initialized_client 