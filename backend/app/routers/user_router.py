"""User search and info routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import UserOut
from ..ws_manager import ws_manager

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=list[UserOut])
def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search users by username, email, or display_name."""
    users = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            User.is_active.is_(True),
            or_(
                User.username.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%"),
            ),
        )
        .limit(20)
        .all()
    )
    return [UserOut.model_validate(u) for u in users]


@router.get("/online", response_model=list[int])
def get_online_users(current_user: User = Depends(get_current_user)):
    """Get list of currently online user IDs (via WebSocket connections)."""
    return ws_manager.get_online_user_ids()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific user's info."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到使用者")
    return UserOut.model_validate(user)
