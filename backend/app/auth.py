from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import re
from threading import Lock
from time import monotonic
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime


# Temporary per-process guard. It reduces accidental bursts but is NOT a
# distributed production rate limiter: use Redis/edge limits before enabling auth.
_attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_attempts_lock = Lock()


def _client_key(request: Request) -> str:
    # Deliberately do not trust X-Forwarded-For unless a trusted proxy policy is configured.
    return request.client.host if request.client else "unknown"


def _check_rate_limit(action: str, request: Request) -> None:
    if action == "register":
        limit = settings.auth_register_limit
        window = float(settings.auth_register_window_seconds)
    elif action == "login":
        limit = settings.auth_login_limit
        window = float(settings.auth_login_window_seconds)
    else:
        raise ValueError("Unknown authentication rate-limit action")
    now = monotonic()
    key = (action, _client_key(request))
    with _attempts_lock:
        bucket = _attempts[key]
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window - (now - bucket[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


def _require_enabled() -> None:
    if not settings.auth_enabled or len(settings.auth_secret_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not enabled. Configure AUTH_ENABLED and a strong AUTH_SECRET_KEY after abuse controls are ready.",
        )


def _public_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, is_active=user.is_active, created_at=user.created_at)


def _create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": user.id, "jti": str(uuid4()), "iat": datetime.now(timezone.utc), "exp": expires},
        settings.auth_secret_key,
        algorithm="HS256",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserResponse:
    _require_enabled()
    _check_rate_limit("register", request)
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, password_hash=password_hash.hash(payload.password), is_active=True)
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(user)
    return _public_user(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    _require_enabled()
    _check_rate_limit("login", request)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not password_hash.verify(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=_create_token(user),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    _require_enabled()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise InvalidTokenError("Missing subject")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"}) from None

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    return user


@router.get("/me", response_model=UserResponse)
def read_current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return _public_user(user)


def get_request_owner(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Allow anonymous access only while auth is explicitly disabled (development prototype)."""
    if not settings.auth_enabled:
        return None
    return get_current_user(token=token, db=db)
