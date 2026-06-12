"""Auth API — register, login, and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.flush()
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a JWT")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead, summary="Get the current authenticated user")
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
