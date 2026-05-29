import pytest


pytestmark = pytest.mark.smoke


def test_user_can_register_login_get_profile_and_logout(api):
    register_response = api.register_user(
        username="alice",
        email="alice@example.com",
        display_name="Alice",
    )
    assert register_response.status_code == 201, register_response.text

    user_id = register_response.json()["user_id"]
    assert api.get_presence_status(user_id) == "offline"

    login_response = api.login_user("alice@example.com")
    assert login_response.status_code == 200, login_response.text
    login_data = login_response.json()
    token = login_data["token"]
    assert login_data["user"]["username"] == "alice"
    assert api.get_presence_status(user_id) == "online"

    me_response = api.client.get("/auth/me", headers=api.auth_headers(token))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"

    logout_response = api.client.post("/auth/logout", headers=api.auth_headers(token))
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "已登出"
    assert api.get_presence_status(user_id) == "offline"

    expired_me_response = api.client.get("/auth/me", headers=api.auth_headers(token))
    assert expired_me_response.status_code == 401, (
        "安全性漏洞：使用者已登出，但舊 Token 竟然還能存取 API！"
    )
    assert expired_me_response.json()["detail"] == "Token 已失效"


def test_register_rejects_duplicate_email_and_username(api):
    first = api.register_user("alice", "alice@example.com", display_name="Alice")
    assert first.status_code == 201, first.text

    duplicate_email = api.register_user("alice2", "alice@example.com", display_name="Alice 2")
    assert duplicate_email.status_code == 400
    assert duplicate_email.json()["detail"] == "此 Email 已被註冊"

    duplicate_username = api.register_user("alice", "other@example.com", display_name="Alice 3")
    assert duplicate_username.status_code == 400
    assert duplicate_username.json()["detail"] == "此使用者名稱已被使用"


def test_login_rejects_invalid_password(api):
    register_response = api.register_user("alice", "alice@example.com")
    assert register_response.status_code == 201, register_response.text

    response = api.client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "帳號或密碼錯誤"


def test_google_login_creates_and_reuses_account(api):
    first_login_response = api.google_login_user("dora@example.com", "Dora")
    assert first_login_response.status_code == 200, first_login_response.text
    first_user = first_login_response.json()["user"]

    assert first_user["auth_provider"] == "google"
    assert first_user["display_name"] == "Dora"
    assert api.get_presence_status(first_user["id"]) == "online"

    second_login_response = api.google_login_user("dora@example.com", "Dora Updated")
    assert second_login_response.status_code == 200, second_login_response.text
    second_user = second_login_response.json()["user"]

    assert second_user["id"] == first_user["id"]
    assert second_user["username"] == first_user["username"]
