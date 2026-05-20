"""Chat room and message routes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models import ChatRoom, ChatRoomMember, Message, User, UserPresence
from ..schemas import ChatRoomCreate, ChatRoomOut, MessageCreate, MessageOut, MessageListResponse, UserOut
from ..auth import get_current_user
from ..ws_manager import ws_manager

router = APIRouter(prefix="/chatrooms", tags=["chatrooms"])


@router.get("", response_model=list[ChatRoomOut])
def get_chatrooms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all chat rooms the current user is a member of, with unread counts."""
    # Get room IDs where user is a member
    memberships = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.user_id == current_user.id)
        .all()
    )

    results = []
    for membership in memberships:
        room = db.query(ChatRoom).filter(ChatRoom.id == membership.room_id).first()
        if not room:
            continue

        # Get member user objects
        room_members = (
            db.query(User)
            .join(ChatRoomMember, ChatRoomMember.user_id == User.id)
            .filter(ChatRoomMember.room_id == room.id)
            .all()
        )

        # Get last message
        last_msg = (
            db.query(Message)
            .filter(Message.room_id == room.id)
            .order_by(Message.created_at.desc())
            .first()
        )

        # Count unread messages (messages after last_read_at)
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.room_id == room.id,
                Message.created_at > membership.last_read_at,
                Message.sender_id != current_user.id,
            )
            .scalar()
        ) or 0

        # For direct chats, use the other person's name as room name
        display_name = room.name
        if room.room_type == "direct":
            other_member = next((m for m in room_members if m.id != current_user.id), None)
            if other_member:
                display_name = other_member.display_name or other_member.username

        last_message_text = None
        if last_msg:
            sender = db.query(User).filter(User.id == last_msg.sender_id).first()
            if room.room_type == "group" and sender:
                last_message_text = f"{sender.display_name or sender.username}: {last_msg.content}"
            else:
                last_message_text = last_msg.content

        results.append(ChatRoomOut(
            id=room.id,
            name=display_name,
            room_type=room.room_type,
            created_by=room.created_by,
            last_message_at=room.last_message_at,
            created_at=room.created_at,
            members=[UserOut.model_validate(m) for m in room_members],
            last_message=last_message_text,
            unread_count=unread_count,
        ))

    # Sort by last_message_at descending
    results.sort(key=lambda r: r.last_message_at or r.created_at, reverse=True)
    return results


@router.post("", response_model=ChatRoomOut, status_code=201)
def create_chatroom(
    req: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat room (direct or group)."""
    if req.room_type == "direct":
        if len(req.member_ids) != 1:
            raise HTTPException(status_code=400, detail="1 對 1 聊天只能指定一個對象")

        other_id = req.member_ids[0]

        # Check if direct chat already exists
        existing = (
            db.query(ChatRoom)
            .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)
            .filter(
                ChatRoom.room_type == "direct",
                ChatRoomMember.user_id == current_user.id,
            )
            .all()
        )
        for room in existing:
            members_ids = [m.user_id for m in room.members]
            if other_id in members_ids and current_user.id in members_ids and len(members_ids) == 2:
                # Return existing room
                room_members = db.query(User).join(ChatRoomMember).filter(ChatRoomMember.room_id == room.id).all()
                other = next((m for m in room_members if m.id != current_user.id), None)
                return ChatRoomOut(
                    id=room.id,
                    name=other.display_name if other else None,
                    room_type=room.room_type,
                    created_by=room.created_by,
                    last_message_at=room.last_message_at,
                    created_at=room.created_at,
                    members=[UserOut.model_validate(m) for m in room_members],
                    last_message=None,
                    unread_count=0,
                )

        # Verify other user exists
        other_user = db.query(User).filter(User.id == other_id).first()
        if not other_user:
            raise HTTPException(status_code=404, detail="找不到該使用者")

    elif req.room_type == "group":
        if not req.name:
            raise HTTPException(status_code=400, detail="群組聊天需要名稱")
        if len(req.member_ids) == 0:
            raise HTTPException(status_code=400, detail="群組聊天至少需要一位其他成員")
    else:
        raise HTTPException(status_code=400, detail="room_type 必須是 'direct' 或 'group'")

    # Create room
    room = ChatRoom(
        name=req.name,
        room_type=req.room_type,
        created_by=current_user.id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # Add current user as member (admin for groups)
    db.add(ChatRoomMember(
        room_id=room.id,
        user_id=current_user.id,
        is_admin=(req.room_type == "group"),
    ))

    # Add other members
    for mid in req.member_ids:
        if mid != current_user.id:
            user = db.query(User).filter(User.id == mid).first()
            if user:
                db.add(ChatRoomMember(room_id=room.id, user_id=mid))

    db.commit()

    # Fetch full member list for response
    room_members = db.query(User).join(ChatRoomMember).filter(ChatRoomMember.room_id == room.id).all()

    display_name = room.name
    if room.room_type == "direct":
        other = next((m for m in room_members if m.id != current_user.id), None)
        display_name = other.display_name if other else None

    return ChatRoomOut(
        id=room.id,
        name=display_name,
        room_type=room.room_type,
        created_by=room.created_by,
        last_message_at=room.last_message_at,
        created_at=room.created_at,
        members=[UserOut.model_validate(m) for m in room_members],
        last_message=None,
        unread_count=0,
    )


@router.get("/{room_id}/messages", response_model=MessageListResponse)
def get_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[int] = Query(None, description="Message ID to paginate before"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get messages for a chat room with cursor-based pagination."""
    # Verify user is a member
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="你不是此聊天室的成員")

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
        result.append(MessageOut(
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            content=msg.content,
            message_type=msg.message_type,
            created_at=msg.created_at,
            sender_name=sender.display_name if sender else None,
        ))

    return MessageListResponse(messages=result, has_more=has_more)


@router.post("/{room_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    room_id: int,
    req: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to a chat room and broadcast via WebSocket."""
    # Verify user is a member
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="你不是此聊天室的成員")

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
    member_ids = [m.user_id for m in db.query(ChatRoomMember).filter(ChatRoomMember.room_id == room_id).all()]
    await ws_manager.send_to_room(
        member_ids=member_ids,
        message={
            "type": "new_message",
            "data": msg_out.model_dump(mode="json"),
        },
    )

    return msg_out


@router.put("/{room_id}/read")
def mark_as_read(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all messages in a chat room as read for the current user."""
    membership = (
        db.query(ChatRoomMember)
        .filter(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="你不是此聊天室的成員")

    membership.last_read_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "已標記為已讀"}
