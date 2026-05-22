"""Authentication routes: register, login, and current user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserPresence
from ..schemas import RegisterRequest, LoginRequest, AuthResponse, UserOut
from ..auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with bcrypt-hashed password."""
    # Check if email already exists
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")

    # Check if username already exists
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="此使用者名稱已被使用")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.username,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create presence record
    presence = UserPresence(user_id=user.id, status="offline")
    db.add(presence)
    db.commit()

    return {"message": "註冊成功", "user_id": user.id}


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password, returns JWT token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_token(user.id, user.email, user.token_version)

    # Update presence to online
    presence = db.query(UserPresence).filter(UserPresence.user_id == user.id).first()
    if presence:
        presence.status = "online"
    db.commit()
    db.refresh(user)

    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current logged-in user info (requires JWT)."""
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout: set user presence to offline."""
    presence = db.query(UserPresence).filter(UserPresence.user_id == current_user.id).first()
    if presence:
        presence.status = "offline"
    current_user.token_version += 1
    db.commit()
    return {"message": "已登出"}
