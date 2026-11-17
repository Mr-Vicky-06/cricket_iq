"""Integration tests for POST /v1/rules/query endpoint."""

import pytest
from fastapi.testclient import TestClient
from cricketiq.backend.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_post_rules_query_success(client):
    payload = {
        "query": "Can a batter be dismissed caught on a free hit in Men's T20I?",
        "context": {
            "format": "T20I",
            "category": "Men's",
            "series_start_date": "2026-10-01"
        },
        "preferences": {
            "detail_level": "standard",
            "max_citations": 3
        }
    }
    response = client.post("/v1/rules/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "answered"
    assert data["answer"] is not None
    assert "summary" in data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["authority"] in ["ICC", "MCC"]
    assert len(data["claims"]) >= 1
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_post_rules_query_domestic_abstention(client):
    payload = {
        "query": "What are the powerplay rules in the Big Bash League?",
    }
    response = client.post("/v1/rules/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "unsupported_competition"
    assert data["answer"] is None
    assert "BBL" in data["abstention_reason"] or "domestic" in data["abstention_reason"].lower()


def test_post_rules_query_invalid_payload(client):
    payload = {
        "query": "x"  # too short (<3 chars)
    }
    response = client.post("/v1/rules/query", json=payload)
    assert response.status_code == 422
