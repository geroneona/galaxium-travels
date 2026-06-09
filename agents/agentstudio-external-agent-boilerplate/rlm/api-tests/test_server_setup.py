"""
Tests for health, readiness and agent card endpoints.
"""

import pytest


class TestHealthAndReadiness:
    def test_health_endpoint_returns_200(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_healthy_status(self, api_client):
        response = api_client.get("/health")
        assert response.json()["status"] == "healthy"

    def test_ready_endpoint_returns_200(self, api_client):
        response = api_client.get("/ready")
        assert response.status_code == 200

    def test_ready_endpoint_returns_ready_status(self, api_client):
        response = api_client.get("/ready")
        assert response.json()["status"] == "ready"


class TestAgentCard:
    def test_agent_card_standard_path_returns_200(self, api_client):
        response = api_client.get("/.well-known/agent-card.json")
        assert response.status_code == 200

    def test_agent_card_standard_path_has_required_fields(self, api_client):
        data = api_client.get("/.well-known/agent-card.json").json()
        for field in ["name", "description", "url", "version"]:
            assert field in data

    def test_agent_card_legacy_path_returns_200(self, api_client):
        response = api_client.get("/.well-known/agent.json")
        assert response.status_code == 200

    def test_both_agent_card_paths_return_same_content(self, api_client):
        standard = api_client.get("/.well-known/agent-card.json").json()
        legacy = api_client.get("/.well-known/agent.json").json()
        assert standard == legacy
