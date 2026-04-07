from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from ..services.bootstrap import ensure_default_project, ensure_wallet
from ..services.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.scalar(select(User).where(User.email == payload.email).limit(1))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    is_first_user = (db.scalar(select(func.count()).select_from(User)) or 0) == 0
    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="admin" if is_first_user else "user",
    )
    db.add(user)
    db.flush()
    wallet = ensure_wallet(db, user)
    ensure_default_project(db, user)
    db.commit()
    db.refresh(user)
    db.refresh(wallet)

    token = create_access_token(user.email, user.role)
    return AuthResponse(
        access_token=token,
        user=UserRead.model_validate(user),
        wallet_balance=str(Decimal(wallet.balance)),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email).limit(1))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    wallet = ensure_wallet(db, user)
    token = create_access_token(user.email, user.role)
    db.commit()
    return AuthResponse(
        access_token=token,
        user=UserRead.model_validate(user),
        wallet_balance=str(Decimal(wallet.balance)),
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
