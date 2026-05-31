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


def test_metrics_endpoint_exposes_prometheus_format(client):
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "chat_web_http_requests_total" in response.text
    assert "chat_web_http_request_duration_seconds_bucket" in response.text


def test_metrics_use_route_templates_for_dynamic_paths(api, client):
    assert api.register_user("alice", "alice@example.com").status_code == 200
    assert api.register_user("bob", "bob@example.com").status_code == 200

    login = api.login_user("alice@example.com")
    token = login.json()["token"]
    bob_id = api.get_user_snapshot(2)["id"]

    room = api.create_room(token, "direct", [bob_id])
    assert room.status_code == 201
    room_id = room.json()["id"]

    send = api.send_message(token, room_id, "hello metrics")
    assert send.status_code == 201

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'chat_web_http_requests_total{method="POST",path="/chatrooms/{room_id}/messages"' in response.text
    assert f'path="/chatrooms/{room_id}/messages"' not in response.text


def test_normalize_metrics_path_collapses_chatroom_routes():
    assert main._normalize_metrics_path("/chatrooms/3/messages") == "/chatrooms/{room_id}/messages"
    assert main._normalize_metrics_path("/chatrooms/3/read") == "/chatrooms/{room_id}/read"
    assert main._normalize_metrics_path("/users/online") == "/users/online"
