"""Configuration and fixtures for API-level tests."""

import os
import pytest
import httpx

BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "local-dev")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "local-client")
KEYCLOAK_TEST_USER = os.getenv("KEYCLOAK_TEST_USER", "testuser")
KEYCLOAK_TEST_PASSWORD = os.getenv("KEYCLOAK_TEST_PASSWORD", "testuser")


def _try_fetch_keycloak_token() -> str | None:
    """Attempt to fetch a bearer token from local Keycloak. Returns None on failure."""
    token_url = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    try:
        resp = httpx.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": KEYCLOAK_CLIENT_ID,
                "username": KEYCLOAK_TEST_USER,
                "password": KEYCLOAK_TEST_PASSWORD,
            },
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


@pytest.fixture
def api_client():
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture(scope="session")
def auth_headers() -> dict:
    """Return Authorization headers for API requests.

    Prefers the ACCESS_TOKEN env var; falls back to fetching a token from the
    local Keycloak instance. Returns an empty dict when neither is available
    so tests can continue without auth (for setups where auth is disabled).
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if access_token:
        return {"Authorization": f"Bearer {access_token}"}
    token = _try_fetch_keycloak_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
