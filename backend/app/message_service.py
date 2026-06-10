"""Message persistence helpers shared by the API and Kafka consumer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import ChatRoom, ChatRoomMember, Message, User
from .schemas import MessageOut


def persist_message_event(db: Session, event: dict[str, Any]) -> Message:
    """Persist a chat message event and update room/member metadata."""
    message = Message(
        room_id=int(event["room_id"]),
        sender_id=int(event["sender_id"]),
        content=str(event["content"]),
        message_type=str(event.get("message_type", "text")),
    )
    db.add(message)

    now = datetime.now(timezone.utc)
    room = db.query(ChatRoom).filter(ChatRoom.id == message.room_id).first()
    if room:
        room.last_message_at = now

    membership = (
        db.query(ChatRoomMember)
        .filter(
            ChatRoomMember.room_id == message.room_id,
            ChatRoomMember.user_id == message.sender_id,
        )
        .first()
    )
    if membership:
        membership.last_read_at = now

    db.commit()
    db.refresh(message)
    return message


def find_persisted_message(db: Session, event: dict[str, Any]) -> Message | None:
    """Find the message created for an event after the consumer commits it."""
    return (
        db.query(Message)
        .filter(
            Message.room_id == int(event["room_id"]),
            Message.sender_id == int(event["sender_id"]),
            Message.content == str(event["content"]),
        )
        .order_by(Message.id.desc())
        .first()
    )


def build_message_out(db: Session, message: Message) -> MessageOut:
    sender = db.query(User).filter(User.id == message.sender_id).first()
    return MessageOut(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        content=message.content,
        message_type=message.message_type,
        created_at=message.created_at,
        sender_name=(sender.display_name or sender.username) if sender else None,
    )
