"""SQLAlchemy ORM models — matches the HackMD PostgreSQL schema."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(Text)
    display_name = Column(String(100))
    avatar_url = Column(Text)
    auth_provider = Column(String(30), default="local")
    provider_user_id = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("ChatRoomMember", back_populates="user")
    messages = relationship("Message", back_populates="sender")
    notifications = relationship("Notification", back_populates="user")
    presence = relationship("UserPresence", back_populates="user", uselist=False)


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    room_type = Column(String(10), nullable=False, default="direct")  # 'direct' | 'group'
    created_by = Column(Integer, ForeignKey("users.id"))
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("ChatRoomMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_chat_rooms_last_message_at", "last_message_at"),
    )


class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_admin = Column(Boolean, default=False)
    last_read_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    room = relationship("ChatRoom", back_populates="members")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_user"),
        Index("idx_chat_room_members_user_id", "user_id"),
        Index("idx_chat_room_members_room_id", "room_id"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(10), default="text")  # 'text' | 'image' | 'file'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_room_created_at", "room_id", "created_at"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    reference_id = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_is_read", "user_id", "is_read"),
    )


class UserPresence(Base):
    __tablename__ = "user_presence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String(10), default="offline")  # 'online' | 'offline' | 'away'
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="presence")

    __table_args__ = (
        Index("idx_user_presence_status", "status"),
    )
