import pytest


pytestmark = pytest.mark.smoke


def test_direct_chat_creation_is_idempotent(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob.json()["user_id"]

    first_room = api.create_room(alice_token, "direct", [bob_id])
    assert first_room.status_code == 201, first_room.text

    second_room = api.create_room(alice_token, "direct", [bob_id])
    assert second_room.status_code == 201, second_room.text
    assert second_room.json()["id"] == first_room.json()["id"]

    rooms_response = api.client.get("/chatrooms", headers=api.auth_headers(alice_token))
    assert rooms_response.status_code == 200
    assert len(rooms_response.json()) == 1


def test_group_chat_requires_name_and_adds_members(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    charlie = api.register_user("charlie", "charlie@example.com", display_name="Charlie")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text
    assert charlie.status_code == 201, charlie.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob.json()["user_id"]
    charlie_id = charlie.json()["user_id"]

    missing_name_response = api.create_room(alice_token, "group", [bob_id, charlie_id])
    assert missing_name_response.status_code == 400
    assert missing_name_response.json()["detail"] == "群組聊天需要名稱"

    empty_members_response = api.create_room(alice_token, "group", [], name="Lonely Room")
    assert empty_members_response.status_code == 400
    assert empty_members_response.json()["detail"] == "群組聊天至少需要一位其他成員"

    room_response = api.create_room(
        alice_token,
        "group",
        [bob_id, charlie_id],
        name="Project X",
    )
    assert room_response.status_code == 201, room_response.text
    room_payload = room_response.json()

    assert room_payload["room_type"] == "group"
    assert room_payload["name"] == "Project X"
    assert len(room_payload["members"]) == 3
    assert api.membership_exists(room_payload["id"], bob_id)
    assert api.membership_exists(room_payload["id"], charlie_id)


def test_group_chat_ignores_malicious_creator_id_in_payload(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    charlie = api.register_user("charlie", "charlie@example.com", display_name="Charlie")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text
    assert charlie.status_code == 201, charlie.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    alice_id = alice_login.json()["user"]["id"]
    bob_id = bob.json()["user_id"]
    charlie_id = charlie.json()["user_id"]

    malicious_response = api.client.post(
        "/chatrooms",
        json={
            "room_type": "group",
            "name": "Hacked Room",
            "member_ids": [charlie_id],
            "creator_id": bob_id,
        },
        headers=api.auth_headers(alice_token),
    )
    assert malicious_response.status_code == 201, malicious_response.text
    payload = malicious_response.json()

    assert payload["created_by"] == alice_id
    assert payload["created_by"] != bob_id
    assert payload["name"] == "Hacked Room"


def test_chatroom_creation_validates_direct_and_room_type_rules(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["token"]
    bob_id = bob.json()["user_id"]

    too_many_members = api.create_room(alice_token, "direct", [bob_id, 999])
    assert too_many_members.status_code == 400
    assert too_many_members.json()["detail"] == "1 對 1 聊天只能指定一個對象"

    missing_user = api.create_room(alice_token, "direct", [999])
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"] == "找不到該使用者"

    invalid_type = api.create_room(alice_token, "broadcast", [bob_id])
    assert invalid_type.status_code == 400
    assert invalid_type.json()["detail"] == "room_type 必須是 'direct' 或 'group'"


def test_chatroom_list_tracks_unread_count_and_latest_order(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice")
    bob = api.register_user("bob", "bob@example.com", display_name="Bob")
    charlie = api.register_user("charlie", "charlie@example.com", display_name="Charlie")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text
    assert charlie.status_code == 201, charlie.text

    alice_login = api.login_user("alice@example.com")
    bob_login = api.login_user("bob@example.com")
    assert alice_login.status_code == 200, alice_login.text
    assert bob_login.status_code == 200, bob_login.text
    alice_token = alice_login.json()["token"]
    bob_token = bob_login.json()["token"]
    bob_id = bob_login.json()["user"]["id"]
    charlie_id = charlie.json()["user_id"]

    direct_room = api.create_room(alice_token, "direct", [bob_id])
    group_room = api.create_room(alice_token, "group", [bob_id, charlie_id], name="Project X")
    assert direct_room.status_code == 201, direct_room.text
    assert group_room.status_code == 201, group_room.text

    direct_room_id = direct_room.json()["id"]
    group_room_id = group_room.json()["id"]

    send_direct = api.send_message(alice_token, direct_room_id, "Direct update")
    assert send_direct.status_code == 201, send_direct.text

    send_group = api.send_message(alice_token, group_room_id, "Group update")
    assert send_group.status_code == 201, send_group.text

    bob_rooms = api.client.get("/chatrooms", headers=api.auth_headers(bob_token))
    assert bob_rooms.status_code == 200
    rooms_payload = bob_rooms.json()

    assert [room["id"] for room in rooms_payload] == [group_room_id, direct_room_id]
    unread_map = {room["id"]: room["unread_count"] for room in rooms_payload}
    assert unread_map[direct_room_id] == 1
    assert unread_map[group_room_id] == 1

    mark_read_response = api.client.put(
        f"/chatrooms/{group_room_id}/read",
        headers=api.auth_headers(bob_token),
    )
    assert mark_read_response.status_code == 200

    refreshed_rooms = api.client.get("/chatrooms", headers=api.auth_headers(bob_token))
    refreshed_unread_map = {room["id"]: room["unread_count"] for room in refreshed_rooms.json()}
    assert refreshed_unread_map[group_room_id] == 0
    assert refreshed_unread_map[direct_room_id] == 1
