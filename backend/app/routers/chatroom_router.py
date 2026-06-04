"""Chat room and message routes."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ChatRoom, ChatRoomMember, Message, User
from ..schemas import (
    ChatRoomCreate,
    ChatRoomOut,
    MessageCreate,
    MessageListResponse,
    MessageOut,
    UserOut,
)
from ..ws_manager import ws_manager

router = APIRouter(prefix="/chatrooms", tags=["chatrooms"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
MessageLimit = Annotated[int, Query(ge=1, le=200)]
MessageBefore = Annotated[int | None, Query(description="Message ID to paginate before")]

BAD_REQUEST_RESPONSE = {400: {"description": "Bad request"}}
FORBIDDEN_RESPONSE = {403: {"description": "Forbidden"}}
NOT_FOUND_RESPONSE = {404: {"description": "Not found"}}
CREATE_CHATROOM_RESPONSES = {
    **BAD_REQUEST_RESPONSE,
    **NOT_FOUND_RESPONSE,
}

DIRECT_ROOM_TYPE = "direct"
GROUP_ROOM_TYPE = "group"
NON_MEMBER_DETAIL = "你不是此聊天室的成員"


def _build_chatroom_out(room: ChatRoom, viewer_id: int, db: Session) -> ChatRoomOut:
    """Build a room response using the viewer's direct-chat display name."""
    room_members = (
        db.query(User)
        .join(ChatRoomMember, ChatRoomMember.user_id == User.id)
        .filter(ChatRoomMember.room_id == room.id)
        .all()
    )

    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room.id, ChatRoomMember.user_id == viewer_id)
        .first()
    )

    last_msg = (
        db.query(Message)
        .filter(Message.room_id == room.id)
        .order_by(Message.created_at.desc())
        .first()
    )

    unread_count = 0
    if membership:
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.room_id == room.id,
                Message.created_at > membership.last_read_at,
                Message.sender_id != viewer_id,
            )
            .scalar()
        ) or 0

    display_name = room.name
    if room.room_type == "direct":
        other_member = next((m for m in room_members if m.id != viewer_id), None)
        if other_member:
            display_name = other_member.display_name or other_member.username

    last_message_text = None
    if last_msg:
        sender = db.query(User).filter(User.id == last_msg.sender_id).first()
        if room.room_type == "group" and sender:
            last_message_text = f"{sender.display_name or sender.username}: {last_msg.content}"
        else:
            last_message_text = last_msg.content

    return ChatRoomOut(
        id=room.id,
        name=display_name,
        room_type=room.room_type,
        created_by=room.created_by,
        last_message_at=room.last_message_at,
        created_at=room.created_at,
        members=[UserOut.model_validate(m) for m in room_members],
        last_message=last_message_text,
        unread_count=unread_count,
    )


@router.get("", response_model=list[ChatRoomOut])
def get_chatrooms(current_user: CurrentUser, db: DbSession):
    """Get all chat rooms the current user is a member of, with unread counts."""
    # Get room IDs where user is a member
    memberships = db.query(ChatRoomMember).filter(ChatRoomMember.user_id == current_user.id).all()

    results = []
    for membership in memberships:
        room = db.query(ChatRoom).filter(ChatRoom.id == membership.room_id).first()
        if not room:
            continue

        results.append(_build_chatroom_out(room, current_user.id, db))

    # Sort by last_message_at descending
    results.sort(key=lambda r: r.last_message_at or r.created_at, reverse=True)
    return results


def _find_existing_direct_room(
    db: Session,
    current_user_id: int,
    other_id: int,
) -> ChatRoom | None:
    existing_rooms = (
        db.query(ChatRoom)
        .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)
        .filter(
            ChatRoom.room_type == DIRECT_ROOM_TYPE,
            ChatRoomMember.user_id == current_user_id,
        )
        .all()
    )
    for room in existing_rooms:
        member_ids = [member.user_id for member in room.members]
        if other_id in member_ids and current_user_id in member_ids and len(member_ids) == 2:
            return room
    return None


def _get_existing_direct_room(
    req: ChatRoomCreate,
    current_user: User,
    db: Session,
) -> ChatRoom | None:
    if len(req.member_ids) != 1:
        raise HTTPException(status_code=400, detail="1 對 1 聊天只能指定一個對象")

    other_id = req.member_ids[0]
    existing_room = _find_existing_direct_room(db, current_user.id, other_id)
    if existing_room:
        return existing_room

    other_user = db.query(User).filter(User.id == other_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="找不到該使用者")

    return None


def _validate_group_chat_request(req: ChatRoomCreate) -> None:
    if not req.name:
        raise HTTPException(status_code=400, detail="群組聊天需要名稱")
    if len(req.member_ids) == 0:
        raise HTTPException(status_code=400, detail="群組聊天至少需要一位其他成員")


def _create_room(db: Session, req: ChatRoomCreate, current_user: User) -> ChatRoom:
    room = ChatRoom(
        name=req.name,
        room_type=req.room_type,
        created_by=current_user.id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def _add_room_members(db: Session, room: ChatRoom, req: ChatRoomCreate, current_user: User) -> None:
    db.add(
        ChatRoomMember(
            room_id=room.id,
            user_id=current_user.id,
            is_admin=(req.room_type == GROUP_ROOM_TYPE),
        )
    )

    for member_id in req.member_ids:
        if member_id == current_user.id:
            continue
        user = db.query(User).filter(User.id == member_id).first()
        if user:
            db.add(ChatRoomMember(room_id=room.id, user_id=member_id))

    db.commit()


def _get_room_member_ids(db: Session, room_id: int) -> list[int]:
    return [
        member.user_id
        for member in db.query(ChatRoomMember).filter(ChatRoomMember.room_id == room_id).all()
    ]


async def _broadcast_chatroom_created(room: ChatRoom, member_ids: list[int], db: Session) -> None:
    for member_id in member_ids:
        room_out = _build_chatroom_out(room, member_id, db)
        await ws_manager.send_to_user(
            member_id,
            {
                "type": "chatroom_created",
                "data": room_out.model_dump(mode="json"),
            },
        )


@router.post(
    "",
    response_model=ChatRoomOut,
    status_code=201,
    responses=CREATE_CHATROOM_RESPONSES,
)
async def create_chatroom(
    req: ChatRoomCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a new chat room (direct or group)."""
    if req.room_type == DIRECT_ROOM_TYPE:
        existing_room = _get_existing_direct_room(req, current_user, db)
        if existing_room:
            return _build_chatroom_out(existing_room, current_user.id, db)
    elif req.room_type == GROUP_ROOM_TYPE:
        _validate_group_chat_request(req)
    else:
        raise HTTPException(status_code=400, detail="room_type 必須是 'direct' 或 'group'")

    room = _create_room(db, req, current_user)
    _add_room_members(db, room, req, current_user)
    await _broadcast_chatroom_created(room, _get_room_member_ids(db, room.id), db)

    return _build_chatroom_out(room, current_user.id, db)


@router.get("/{room_id}/messages", response_model=MessageListResponse, responses=FORBIDDEN_RESPONSE)
def get_messages(
    room_id: int,
    current_user: CurrentUser,
    db: DbSession,
    limit: MessageLimit = 50,
    before: MessageBefore = None,
):
    """Get messages for a chat room with cursor-based pagination."""
    # Verify user is a member
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail=NON_MEMBER_DETAIL)

    query = db.query(Message).filter(Message.room_id == room_id)

    if before:
        query = query.filter(Message.id < before)

    messages = query.order_by(Message.created_at.desc()).limit(limit + 1).all()

    has_more = len(messages) > limit
    messages = messages[:limit]
    messages.reverse()  # Return in chronological order

    result = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        result.append(
            MessageOut(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                content=msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at,
                sender_name=sender.display_name if sender else None,
            )
        )

    return MessageListResponse(messages=result, has_more=has_more)


@router.post(
    "/{room_id}/messages",
    response_model=MessageOut,
    status_code=201,
    responses=FORBIDDEN_RESPONSE,
)
async def send_message(
    room_id: int,
    req: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Send a message to a chat room and broadcast via WebSocket."""
    # Verify user is a member
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail=NON_MEMBER_DETAIL)

    # Create message
    message = Message(
        room_id=room_id,
        sender_id=current_user.id,
        content=req.content,
        message_type="text",
    )
    db.add(message)

    # Update room's last_message_at
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if room:
        room.last_message_at = datetime.now(timezone.utc)

    # Update sender's last_read_at
    membership.last_read_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(message)

    msg_out = MessageOut(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        content=message.content,
        message_type=message.message_type,
        created_at=message.created_at,
        sender_name=current_user.display_name or current_user.username,
    )

    # Broadcast via WebSocket to all room members
    member_ids = _get_room_member_ids(db, room_id)
    await ws_manager.send_to_room(
        member_ids=member_ids,
        message={
            "type": "new_message",
            "data": msg_out.model_dump(mode="json"),
        },
    )

    return msg_out


@router.put("/{room_id}/read", responses=FORBIDDEN_RESPONSE)
def mark_as_read(
    room_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark all messages in a chat room as read for the current user."""
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail=NON_MEMBER_DETAIL)

    membership.last_read_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "已標記為已讀"}
