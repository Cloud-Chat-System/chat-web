import pytest


pytestmark = pytest.mark.smoke


def test_user_search_and_get_user(api):
    alice = api.register_user("alice", "alice@example.com", display_name="Alice Chen")
    bob = api.register_user("bobby", "bob@example.com", display_name="Bob Lin")
    carol = api.register_user("carol", "carol@example.com", display_name="Carol Wang")
    assert alice.status_code == 201, alice.text
    assert bob.status_code == 201, bob.text
    assert carol.status_code == 201, carol.text

    alice_login = api.login_user("alice@example.com")
    assert alice_login.status_code == 200, alice_login.text
    token = alice_login.json()["token"]

    search_by_name = api.client.get(
        "/users/search",
        params={"q": "Bob"},
        headers=api.auth_headers(token),
    )
    assert search_by_name.status_code == 200
    search_payload = search_by_name.json()
    assert len(search_payload) == 1
    assert search_payload[0]["username"] == "bobby"

    search_by_email = api.client.get(
        "/users/search",
        params={"q": "carol@"},
        headers=api.auth_headers(token),
    )
    assert search_by_email.status_code == 200
    assert search_by_email.json()[0]["username"] == "carol"

    search_self = api.client.get(
        "/users/search",
        params={"q": "alice"},
        headers=api.auth_headers(token),
    )
    assert search_self.status_code == 200
    assert search_self.json() == []

    bob_id = bob.json()["user_id"]
    user_response = api.client.get(f"/users/{bob_id}", headers=api.auth_headers(token))
    assert user_response.status_code == 200
    assert user_response.json()["display_name"] == "Bob Lin"

    missing_response = api.client.get("/users/9999", headers=api.auth_headers(token))
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "找不到使用者"
