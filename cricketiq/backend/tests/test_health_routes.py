"""Unit and integration tests for API health routes."""

import pytest
from fastapi.testclient import TestClient
from cricketiq.backend.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_liveness_endpoint(client):
    """Test GET /health/live returns 200 OK."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_readiness_endpoint(client):
    """Test GET /health/ready returns database connection status."""
    response = client.get("/health/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    if response.status_code == 200:
        assert data["database"] == "connected"
        assert "clauses_count" in data
