"""
Configuration and fixtures for API-level tests.
"""

import os
import pytest
import httpx

# Base URL for API tests - allows override via environment variable
BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_client():
    """Provide an HTTP client for API tests."""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture
async def async_api_client():
    """Provide an async HTTP client for API tests."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client
