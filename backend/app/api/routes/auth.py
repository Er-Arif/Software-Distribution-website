from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.models import RefreshToken, Role, User
from app.schemas import LoginRequest, RegisterRequest, TokenPair
from app.services.events import emit_event

router = APIRouter()


@router.post("/register", response_model=TokenPair, dependencies=[Depends(rate_limit("auth"))])
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    role = db.scalar(select(Role).where(Role.name == "customer"))
    if not role:
        role = Role(name="customer", description="Customer")
        db.add(role)
        db.flush()
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        roles=[role],
    )
    db.add(user)
    db.flush()
    refresh, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=sha256(refresh.encode()).hexdigest(), expires_at=expires_at))
    emit_event(db, "user.registered", "user", str(user.id), {})
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, ["customer"]), refresh_token=refresh)


@router.post("/login", response_model=TokenPair, dependencies=[Depends(rate_limit("auth"))])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if not user or not verify_password(payload.password, user.password_hash):
        emit_event(db, "auth.login_failed", "user", None, {"email": payload.email})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    roles = [role.name for role in user.roles]
    refresh, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=sha256(refresh.encode()).hexdigest(), expires_at=expires_at))
    emit_event(db, "auth.login_success", "user", str(user.id), {})
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, roles), refresh_token=refresh)
