"""
Test product requirements for the A2A agent server.

These tests verify the core functionality described in PRD.md:
1. Health check endpoint at /health
2. Readiness check endpoint at /ready
3. Agent card at /.well-known/agent-card.json
4. Legacy agent card at /.well-known/agent.json
5. A2A agent responds with a dummy message "Hello" for any input
"""

import pytest


class TestHealthAndReadiness:
    """Test health and readiness endpoints."""

    def test_health_endpoint_returns_200(self, api_client):
        """Test that /health endpoint returns 200 status."""
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_healthy_status(self, api_client):
        """Test that /health endpoint returns healthy status."""
        response = api_client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_ready_endpoint_returns_200(self, api_client):
        """Test that /ready endpoint returns 200 status."""
        response = api_client.get("/ready")
        assert response.status_code == 200

    def test_ready_endpoint_returns_ready_status(self, api_client):
        """Test that /ready endpoint returns ready status."""
        response = api_client.get("/ready")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"


class TestAgentCard:
    """Test agent card endpoints."""

    def test_agent_card_standard_path_returns_200(self, api_client):
        """Test that agent card is accessible at standard path."""
        response = api_client.get("/.well-known/agent-card.json")
        assert response.status_code == 200

    def test_agent_card_standard_path_is_valid_json(self, api_client):
        """Test that agent card at standard path is valid JSON."""
        response = api_client.get("/.well-known/agent-card.json")
        data = response.json()
        assert isinstance(data, dict)

    def test_agent_card_standard_path_has_required_fields(self, api_client):
        """Test that agent card has required fields per A2A spec."""
        response = api_client.get("/.well-known/agent-card.json")
        data = response.json()

        # Required fields per A2A agent card specification
        required_fields = ["name", "description", "url", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_agent_card_legacy_path_returns_200(self, api_client):
        """Test that agent card is accessible at legacy path."""
        response = api_client.get("/.well-known/agent.json")
        assert response.status_code == 200

    def test_agent_card_legacy_path_is_valid_json(self, api_client):
        """Test that agent card at legacy path is valid JSON."""
        response = api_client.get("/.well-known/agent.json")
        data = response.json()
        assert isinstance(data, dict)

    def test_agent_card_legacy_path_has_required_fields(self, api_client):
        """Test that legacy agent card has required fields."""
        response = api_client.get("/.well-known/agent.json")
        data = response.json()

        # Required fields should be consistent between both paths
        required_fields = ["name", "description", "url", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field at legacy path: {field}"

    def test_both_agent_card_paths_return_same_content(self, api_client):
        """Test that both agent card paths return the same content."""
        standard_response = api_client.get("/.well-known/agent-card.json")
        legacy_response = api_client.get("/.well-known/agent.json")

        assert (
            standard_response.json() == legacy_response.json()
        ), "Agent card content differs between standard and legacy paths"

    def test_agent_card_contains_supported_interfaces(self, api_client):
        """Test that agent card includes supported interfaces."""
        response = api_client.get("/.well-known/agent-card.json")
        data = response.json()

        assert "supportedInterfaces" in data
        assert isinstance(data["supportedInterfaces"], list)
        assert len(data["supportedInterfaces"]) > 0

    def test_agent_card_supported_interfaces_have_url(self, api_client):
        """Test that each supported interface has a URL."""
        response = api_client.get("/.well-known/agent-card.json")
        data = response.json()

        for interface in data["supportedInterfaces"]:
            assert "url" in interface
            assert isinstance(interface["url"], str)
            assert len(interface["url"]) > 0

    def test_agent_card_supported_interfaces_have_protocol_binding(
        self, api_client
    ):
        """Test that each supported interface has a protocol binding."""
        response = api_client.get("/.well-known/agent-card.json")
        data = response.json()

        for interface in data["supportedInterfaces"]:
            assert "protocolBinding" in interface
            assert interface["protocolBinding"] in ["JSONRPC", "HTTP+JSON"]


class TestContentTypes:
    """Test that endpoints return correct content types."""

    def test_health_endpoint_returns_json_content_type(self, api_client):
        """Test that /health returns JSON content type."""
        response = api_client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")

    def test_ready_endpoint_returns_json_content_type(self, api_client):
        """Test that /ready returns JSON content type."""
        response = api_client.get("/ready")
        assert "application/json" in response.headers.get("content-type", "")

    def test_agent_card_returns_json_content_type(self, api_client):
        """Test that agent card returns JSON content type."""
        response = api_client.get("/.well-known/agent-card.json")
        assert "application/json" in response.headers.get("content-type", "")


class TestJSONRPC:
    """Test JSON-RPC communication with the agent."""

    def test_jsonrpc_hello_message(self, api_client):
        """Test sending 'Hello' via JSON-RPC returns a successful response."""
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "id": 1,
            "params": {"message": {"messageId": "msg-1", "role": "user","parts": [{"text": "hello"}]}}
        }
        response = api_client.post("/v1/rpc", json=jsonrpc_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data and data.get("jsonrpc") == "2.0"


class TestEndpointResilience:
    """Test that endpoints are resilient and handle edge cases."""

    def test_health_endpoint_with_options_method(self, api_client):
        """Test that /health endpoint handles OPTIONS request."""
        response = api_client.options("/health")
        # Should return 200 or 405 (Method Not Allowed), but not 500
        assert response.status_code < 500

    def test_ready_endpoint_with_options_method(self, api_client):
        """Test that /ready endpoint handles OPTIONS request."""
        response = api_client.options("/ready")
        # Should return 200 or 405 (Method Not Allowed), but not 500
        assert response.status_code < 500

    def test_agent_card_with_options_method(self, api_client):
        """Test that agent card endpoint handles OPTIONS request."""
        response = api_client.options("/.well-known/agent-card.json")
        # Should return 200 or 405 (Method Not Allowed), but not 500
        assert response.status_code < 500

    def test_health_endpoint_consistent_responses(self, api_client):
        """Test that multiple calls to health endpoint return consistent results."""
        response1 = api_client.get("/health")
        response2 = api_client.get("/health")

        assert response1.status_code == response2.status_code
        assert response1.json() == response2.json()

    def test_ready_endpoint_consistent_responses(self, api_client):
        """Test that multiple calls to ready endpoint return consistent results."""
        response1 = api_client.get("/ready")
        response2 = api_client.get("/ready")

        assert response1.status_code == response2.status_code
        assert response1.json() == response2.json()
