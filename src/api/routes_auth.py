"""
Authentication routes - register, login, refresh, logout, profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .db_models import User, RefreshToken
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token_value,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: Optional[str] = Field(None, max_length=254)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str]


class UpdateProfileRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account and return tokens."""
    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    # Check email uniqueness (if provided)
    if body.email:
        existing_email = await db.execute(select(User).where(User.email == body.email))
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # get user.id

    # Create tokens
    access = create_access_token(user.id, user.username)
    refresh_value, refresh_expires = create_refresh_token_value()
    db.add(
        RefreshToken(user_id=user.id, token=refresh_value, expires_at=refresh_expires)
    )

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_value,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with username + password and receive tokens."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access = create_access_token(user.id, user.username)
    refresh_value, refresh_expires = create_refresh_token_value()
    db.add(
        RefreshToken(user_id=user.id, token=refresh_value, expires_at=refresh_expires)
    )

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_value,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token == body.refresh_token)
        .where(RefreshToken.revoked == False)  # noqa: E712
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old refresh token (rotation)
    stored.revoked = True

    # Load user
    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Issue new tokens
    access = create_access_token(user.id, user.username)
    new_refresh, new_expires = create_refresh_token_value()
    db.add(RefreshToken(user_id=user.id, token=new_refresh, expires_at=new_expires))

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.post("/logout", status_code=204)
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all refresh tokens for the current user."""
    from sqlalchemy import update

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .where(RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    return None


@router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserProfile(id=user.id, username=user.username, email=user.email)


@router.put("/me", response_model=UserProfile)
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's email and/or password."""
    if body.email is not None:
        # Check email uniqueness
        existing = await db.execute(
            select(User).where(User.email == body.email, User.id != user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = body.email

    if body.password is not None:
        user.hashed_password = hash_password(body.password)

    db.add(user)
    return UserProfile(id=user.id, username=user.username, email=user.email)
