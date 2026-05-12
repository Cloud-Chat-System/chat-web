"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: "UserOut"


class GoogleLoginRequest(BaseModel):
    """Simulated Google login — in production, this would be an OAuth code exchange."""
    email: EmailStr
    name: str


# ── User ──────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str = "local"
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


# ── ChatRoom ─────────────────────────────────────────

class ChatRoomCreate(BaseModel):
    room_type: str = "direct"  # 'direct' | 'group'
    name: Optional[str] = None  # Required for group, optional for direct
    member_ids: List[int]  # User IDs to add


class ChatRoomOut(BaseModel):
    id: int
    name: Optional[str] = None
    room_type: str
    created_by: Optional[int] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    members: List[UserOut] = []
    last_message: Optional[str] = None
    unread_count: int = 0

    model_config = {"from_attributes": True}


# ── Message ──────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    content: str
    message_type: str = "text"
    created_at: datetime
    sender_name: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: List[MessageOut]
    has_more: bool = False
