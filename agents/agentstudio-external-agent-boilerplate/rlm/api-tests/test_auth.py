"""
Tests for Keycloak-based bearer token authorization.

Requires:
 - Agent running with KEYCLOAK_ISSUER_URL / KEYCLOAK_JWKS_URL set to local Keycloak.
 - Local Keycloak running (started via `make ensure-local-keycloak` or `make dev`).
   Realm: local-dev, client: local-client, user: testuser / testuser

These tests are skipped when local Keycloak is not accessible so they do not
block CI environments without a local Keycloak instance.
"""

import os

import httpx
import pytest

BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")
RPC_PATH = os.getenv("RPC_PATH", "/v1/rpc")

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "local-dev")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "local-client")
KEYCLOAK_TEST_USER = os.getenv("KEYCLOAK_TEST_USER", "testuser")
KEYCLOAK_TEST_PASSWORD = os.getenv("KEYCLOAK_TEST_PASSWORD", "testuser")

_TOKEN_URL = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

A2A_BEARER_TOKEN = os.getenv("A2A_BEARER_TOKEN", 'local-test-token')


def _fetch_token() -> str:
    """Obtain a bearer token from local Keycloak using password grant."""
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "username": KEYCLOAK_TEST_USER,
            "password": KEYCLOAK_TEST_PASSWORD,
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _make_send_request(text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": "test-auth-1",
        "params": {
            "message": {
                "messageId": "msg-auth-001",
                "role": "user",
                "kind": "message",
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }


@pytest.fixture(scope="module")
def keycloak_token():
    """Obtain a valid Keycloak token; skip the module if Keycloak is not reachable."""
    try:
        token = _fetch_token()
    except Exception as exc:
        pytest.skip(f"Local Keycloak not accessible at {KEYCLOAK_BASE_URL}: {exc}")
    return token


class TestAuth:
    """Auth test"""

    def test_message_send_with_valid_bearer_token_returns_200(self):
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            response = client.post(
                RPC_PATH,
                json= _make_send_request("Hello"),
                headers={"Authorization": f"Bearer {A2A_BEARER_TOKEN}"},
            )
        assert response.status_code == 200, (
            f"Expected 200 with valid A2A bearer token, got {response.status_code}: {response.text}"
        )

    def test_message_send_with_valid_token_returns_200(self, keycloak_token):
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            response = client.post(
                RPC_PATH,
                json=_make_send_request("Hello"),
                headers={"Authorization": f"Bearer {keycloak_token}"},
            )
        assert response.status_code == 200, (
            f"Expected 200 with valid token, got {response.status_code}: {response.text}"
        )


    def test_message_send_without_token_returns_401(self):
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            response = client.post(RPC_PATH, json=_make_send_request("Hello"))
        assert response.status_code == 401, (
            f"Expected 401 without token, got {response.status_code}: {response.text}"
        )

