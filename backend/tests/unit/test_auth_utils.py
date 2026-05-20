import jwt
import pytest
from fastapi import HTTPException

from app.auth import create_token, decode_token, hash_password, verify_password
from app.config import JWT_ALGORITHM, JWT_SECRET


pytestmark = pytest.mark.unit


def test_hash_password_and_verify_password():
    password = "password123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("password123")

    assert verify_password("wrong-password", hashed) is False


def test_create_token_and_decode_token_round_trip():
    token = create_token(7, "alice@example.com")
    payload = decode_token(token)

    assert payload["sub"] == "7"
    assert payload["email"] == "alice@example.com"


def test_decode_token_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-real-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "無效的 Token"


def test_decode_token_rejects_expired_token():
    expired_token = jwt.encode(
        {"sub": "7", "email": "alice@example.com", "exp": 1, "iat": 1},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(expired_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token 已過期"
