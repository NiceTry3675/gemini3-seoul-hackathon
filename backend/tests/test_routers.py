"""Tests for health endpoint, CORS, and DomainException error format."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthRouter:
    def test_health_returns_ok(self, test_client):
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_content_type_is_json(self, test_client):
        response = test_client.get("/api/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------

class TestCORS:
    def test_cors_header_present_on_health(self, test_client):
        response = test_client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_all_origins(self, test_client):
        response = test_client.get(
            "/api/health",
            headers={"Origin": "http://example.com"},
        )
        assert response.headers.get("access-control-allow-origin") == "*"

    def test_cors_options_preflight(self, test_client):
        response = test_client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # OPTIONS should return 200 or 204 for preflight
        assert response.status_code in (200, 204)


# ---------------------------------------------------------------------------
# DomainException error format
# ---------------------------------------------------------------------------

class TestDomainExceptionFormat:
    def test_quota_exceeded_error_format(self, test_client, mock_genai_client):
        """QuotaExceededError should return JSON {"error": "..."} with status 429."""
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 429
        body = response.json()
        assert "error" in body
        assert isinstance(body["error"], str)

    def test_safety_block_error_format(self, test_client, mock_genai_client):
        """SafetyBlockError should return JSON {"error": "..."} with status 422."""
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety block")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 422
        body = response.json()
        assert "error" in body

    def test_gemini_api_error_format(self, test_client, mock_genai_client):
        """GeminiAPIError should return JSON {"error": "..."} with status 502."""
        mock_genai_client.aio.models.generate_content.side_effect = Exception("network failure")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 502
        body = response.json()
        assert "error" in body

    def test_error_body_has_no_extra_fields(self, test_client, mock_genai_client):
        """Error responses should only contain the 'error' key."""
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        body = response.json()
        # Only "error" key should be present
        assert list(body.keys()) == ["error"]

    def test_404_for_unknown_endpoint(self, test_client):
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client):
        # GET on a POST-only endpoint
        response = test_client.get("/api/text/generate")
        assert response.status_code == 405
