import pytest

from app import main


pytestmark = pytest.mark.unit


def test_health_endpoint_returns_liveness(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "TSMC Messenger API",
    }


def test_api_health_returns_readiness_when_database_is_available(client, monkeypatch):
    monkeypatch.setattr(main, "_check_database_health", lambda: (True, "ok"))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "TSMC Messenger API",
        "status": "ok",
        "database": "ok",
    }


def test_api_health_returns_503_when_database_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(main, "_check_database_health", lambda: (False, "unavailable"))

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "service": "TSMC Messenger API",
        "status": "degraded",
        "database": "unavailable",
    }


def test_health_endpoint_stays_200_even_if_database_checker_fails(client, monkeypatch):
    monkeypatch.setattr(main, "_check_database_health", lambda: (False, "unavailable"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
