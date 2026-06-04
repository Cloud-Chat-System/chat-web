"""Authentication routes: register, login, and current user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserPresence
from ..schemas import RegisterRequest, LoginRequest, GoogleLoginRequest, AuthResponse, UserOut
from ..auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

BAD_REQUEST_RESPONSE = {400: {"description": "Bad request"}}
UNAUTHORIZED_RESPONSE = {401: {"description": "Unauthorized"}}


def _ensure_presence(db: Session, user: User, status_value: str) -> None:
    presence = db.query(UserPresence).filter(UserPresence.user_id == user.id).first()
    if presence:
        presence.status = status_value
        return
    db.add(UserPresence(user_id=user.id, status=status_value))


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses=BAD_REQUEST_RESPONSE,
)
def register(req: RegisterRequest, db: DbSession):
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

    _ensure_presence(db, user, "offline")
    db.commit()

    return {"message": "註冊成功", "user_id": user.id}


@router.post("/login", response_model=AuthResponse, responses=UNAUTHORIZED_RESPONSE)
def login(req: LoginRequest, db: DbSession):
    """Login with email and password, returns JWT token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_token(user.id, user.email, user.token_version)

    _ensure_presence(db, user, "online")
    db.commit()
    db.refresh(user)

    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@router.post("/google", response_model=AuthResponse)
def google_login(req: GoogleLoginRequest, db: DbSession):
    """Create or reuse a Google-backed account and return a JWT token."""
    user = db.query(User).filter(User.email == req.email).first()
    if user is None:
        username_base = req.email.split("@", 1)[0]
        username = username_base
        suffix = 1
        while db.query(User).filter(User.username == username).first():
            suffix += 1
            username = f"{username_base}{suffix}"

        user = User(
            username=username,
            email=req.email,
            password_hash=None,
            display_name=req.name,
            auth_provider="google",
            provider_user_id=req.email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.auth_provider != "google":
        user.auth_provider = "google"
        user.provider_user_id = user.provider_user_id or req.email

    _ensure_presence(db, user, "online")
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.email, user.token_version)
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: CurrentUser):
    """Get current logged-in user info (requires JWT)."""
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout(current_user: CurrentUser, db: DbSession):
    """Logout: set user presence to offline."""
    _ensure_presence(db, current_user, "offline")
    current_user.token_version += 1
    db.commit()
    return {"message": "已登出"}
