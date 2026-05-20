import pytest


pytestmark = pytest.mark.smoke


def test_send_list_and_mark_read_flow(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text

    alice_login = api.login_user("alice@example.com")
    bob_login = api.login_user("bob@example.com")
    assert alice_login.status_code == 200, alice_login.text
    assert bob_login.status_code == 200, bob_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob_login.json()["user"]["id"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_payload = room_response.json()
    room_id = room_payload["id"]
    assert room_payload["room_type"] == "direct"
    assert len(room_payload["members"]) == 2

    message_response = api.send_message(alice_token, room_id, "Hello Bob")
    assert message_response.status_code == 201, message_response.text
    assert message_response.json()["content"] == "Hello Bob"

    messages_response = api.client.get(
        f"/chatrooms/{room_id}/messages",
        headers=api.auth_headers(alice_token),
    )
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()
    assert len(messages_payload["messages"]) == 1
    assert messages_payload["messages"][0]["content"] == "Hello Bob"
    assert messages_payload["has_more"] is False

    mark_read_response = api.client.put(
        f"/chatrooms/{room_id}/read",
        headers=api.auth_headers(alice_token),
    )
    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["message"] == "已標記為已讀"


def test_message_pagination_supports_before_cursor(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    assert bob.status_code == 201, bob.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob.json()["user_id"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    for content in ["msg-1", "msg-2", "msg-3"]:
        message_response = api.send_message(alice_token, room_id, content)
        assert message_response.status_code == 201, message_response.text

    first_page = api.client.get(
        f"/chatrooms/{room_id}/messages",
        params={"limit": 2},
        headers=api.auth_headers(alice_token),
    )
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["has_more"] is True
    assert [msg["content"] for msg in first_payload["messages"]] == ["msg-2", "msg-3"]

    cursor = first_payload["messages"][0]["id"]
    second_page = api.client.get(
        f"/chatrooms/{room_id}/messages",
        params={"limit": 2, "before": cursor},
        headers=api.auth_headers(alice_token),
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["has_more"] is False
    assert [msg["content"] for msg in second_payload["messages"]] == ["msg-1"]


def test_send_message_rejects_empty_content(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    assert bob.status_code == 201, bob.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob.json()["user_id"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    empty_message_response = api.send_message(alice_token, room_id, "")
    assert empty_message_response.status_code == 422


def test_message_endpoints_reject_non_member_access(api):
    api.register_user("alice", "alice@example.com", display_name="Alice")
    api.register_user("bob", "bob@example.com", display_name="Bob")
    api.register_user("carol", "carol@example.com", display_name="Carol")

    alice_login = api.login_user("alice@example.com")
    bob_login = api.login_user("bob@example.com")
    carol_login = api.login_user("carol@example.com")
    assert alice_login.status_code == 200, alice_login.text
    assert bob_login.status_code == 200, bob_login.text
    assert carol_login.status_code == 200, carol_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob_login.json()["user"]["id"]
    carol_token = carol_login.json()["token"]

    room_response = api.create_room(alice_token, "direct", [bob_id])
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    unauthorized_get = api.client.get(
        f"/chatrooms/{room_id}/messages",
        headers=api.auth_headers(carol_token),
    )
    assert unauthorized_get.status_code == 403
    assert unauthorized_get.json()["detail"] == "你不是此聊天室的成員"

    unauthorized_send = api.send_message(carol_token, room_id, "Should fail")
    assert unauthorized_send.status_code == 403
    assert unauthorized_send.json()["detail"] == "你不是此聊天室的成員"

    unauthorized_read = api.client.put(
        f"/chatrooms/{room_id}/read",
        headers=api.auth_headers(carol_token),
    )
    assert unauthorized_read.status_code == 403
    assert unauthorized_read.json()["detail"] == "你不是此聊天室的成員"
