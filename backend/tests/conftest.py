import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT
TEST_DB_PATH = ROOT / "tests" / "requirements_test.db"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "requirements-test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_HOURS"] = "24"

from app.database import SessionLocal, engine
from app.main import app
from app.models import ChatRoomMember, User, UserPresence
from app.sql_scripts import apply_init_schema
from app.ws_manager import ws_manager


class BackendTestHelper:
    def __init__(self, client: TestClient):
        self.client = client

    def register_user(
        self,
        username: str,
        email: str,
        password: str = "password123",
        display_name: Optional[str] = None,
    ):
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "display_name": display_name or username.title(),
        }
        return self.client.post("/auth/register", json=payload)

    def login_user(self, email: str, password: str = "password123"):
        return self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )

    def google_login_user(self, email: str, name: str):
        return self.client.post("/auth/google", json={"email": email, "name": name})

    @staticmethod
    def auth_headers(token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def create_room(
        self,
        token: str,
        room_type: str,
        member_ids: List[int],
        name: Optional[str] = None,
    ):
        payload = {"room_type": room_type, "member_ids": member_ids}
        if name is not None:
            payload["name"] = name
        return self.client.post(
            "/chatrooms",
            json=payload,
            headers=self.auth_headers(token),
        )

    def send_message(self, token: str, room_id: int, content: str):
        return self.client.post(
            f"/chatrooms/{room_id}/messages",
            json={"content": content},
            headers=self.auth_headers(token),
        )

    def get_presence_status(self, user_id: int) -> Optional[str]:
        with SessionLocal() as session:
            presence = session.query(UserPresence).filter(UserPresence.user_id == user_id).first()
            return presence.status if presence else None

    def membership_exists(self, room_id: int, user_id: int) -> bool:
        with SessionLocal() as session:
            return (
                session.query(ChatRoomMember)
                .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == user_id)
                .first()
                is not None
            )

    def get_user_snapshot(self, user_id: int):
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
            }


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_database(request):
    if request.node.get_closest_marker("pressure"):
        yield
        return

    ws_manager.active_connections.clear()
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    apply_init_schema(target_engine=engine)
    yield
    ws_manager.active_connections.clear()
    engine.dispose()

 
@pytest.fixture
def api(client):
    return BackendTestHelper(client)
