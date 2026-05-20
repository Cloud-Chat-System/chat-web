import pytest


pytestmark = pytest.mark.smoke


def test_alice_sends_direct_message_to_bob_and_marks_read(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    api.register_user("bob", "bob@example.com", display_name="Bob")

    alice_login = api.login_user("alice@example.com")
    bob_login = api.login_user("bob@example.com")
    assert alice_login.status_code == 200, alice_login.text
    assert bob_login.status_code == 200, bob_login.text
    alice_token = alice_login.json()["token"]
    bob_token = bob_login.json()["token"]
    bob_id = bob_login.json()["user"]["id"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    send_response = api.send_message(alice_token, room_id, "Hello Bob")
    assert send_response.status_code == 201, send_response.text

    bob_rooms = api.client.get("/chatrooms", headers=api.auth_headers(bob_token))
    assert bob_rooms.status_code == 200
    assert bob_rooms.json()[0]["unread_count"] == 1

    bob_messages = api.client.get(
        f"/chatrooms/{room_id}/messages",
        headers=api.auth_headers(bob_token),
    )
    assert bob_messages.status_code == 200
    assert bob_messages.json()["messages"][0]["content"] == "Hello Bob"

    mark_read_response = api.client.put(
        f"/chatrooms/{room_id}/read",
        headers=api.auth_headers(bob_token),
    )
    assert mark_read_response.status_code == 200

    refreshed_rooms = api.client.get("/chatrooms", headers=api.auth_headers(bob_token))
    assert refreshed_rooms.status_code == 200
    assert refreshed_rooms.json()[0]["unread_count"] == 0


def test_websocket_ping_and_online_user_tracking(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    login_response = api.login_user("alice@example.com")
    assert login_response.status_code == 200, login_response.text
    login_data = login_response.json()
    token = login_data["token"]
    user_id = login_data["user"]["id"]

    with api.client.websocket_connect("/ws") as websocket:
        websocket.send_json({"token": token})
        connected = websocket.receive_json()
        assert connected["type"] == "connected"
        assert connected["user_id"] == user_id
        assert api.get_presence_status(user_id) == "online"

        online_response = api.client.get("/users/online", headers=api.auth_headers(token))
        assert online_response.status_code == 200
        assert user_id in online_response.json()

        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"

    online_after_disconnect = api.client.get("/users/online", headers=api.auth_headers(token))
    assert online_after_disconnect.status_code == 200
    assert user_id not in online_after_disconnect.json()
    assert api.get_presence_status(user_id) == "offline"


def test_websocket_broadcasts_presence_and_new_messages(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    api.register_user("bob", "bob@example.com", display_name="Bob")

    alice_login = api.login_user("alice@example.com")
    bob_login = api.login_user("bob@example.com")
    assert alice_login.status_code == 200, alice_login.text
    assert bob_login.status_code == 200, bob_login.text
    alice_token = alice_login.json()["token"]
    bob_token = bob_login.json()["token"]
    alice_id = alice_login.json()["user"]["id"]
    bob_id = bob_login.json()["user"]["id"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    with api.client.websocket_connect("/ws") as bob_ws:
        bob_ws.send_json({"token": bob_token})
        bob_connected = bob_ws.receive_json()
        assert bob_connected["type"] == "connected"

        with api.client.websocket_connect("/ws") as alice_ws:
            alice_ws.send_json({"token": alice_token})

            bob_presence = bob_ws.receive_json()
            assert bob_presence["type"] == "presence"
            assert bob_presence["user_id"] == alice_id
            assert bob_presence["status"] == "online"

            alice_connected = alice_ws.receive_json()
            assert alice_connected["type"] == "connected"

            send_response = api.send_message(alice_token, room_id, "real-time hello")
            assert send_response.status_code == 201, send_response.text

            bob_message = bob_ws.receive_json()
            assert bob_message["type"] == "new_message"
            assert bob_message["data"]["content"] == "real-time hello"
            assert bob_message["data"]["room_id"] == room_id

        bob_offline_presence = bob_ws.receive_json()
        assert bob_offline_presence["type"] == "presence"
        assert bob_offline_presence["user_id"] == alice_id
        assert bob_offline_presence["status"] == "offline"
