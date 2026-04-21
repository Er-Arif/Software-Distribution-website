from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, hash_token, verify_password
from app.db.models import RefreshToken, Role, User
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
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
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires_at))
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
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires_at))
    emit_event(db, "auth.login_success", "user", str(user.id), {})
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, roles), refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(rate_limit("auth"))])
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token_hash = hash_token(payload.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None)))
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token has been rotated or revoked")
    user = db.scalar(select(User).where(User.id == stored.user_id, User.deleted_at.is_(None)))
    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    stored.revoked_at = func.now()
    roles = [role.name for role in user.roles]
    new_refresh, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(new_refresh), expires_at=expires_at))
    emit_event(db, "auth.token_refreshed", "user", str(user.id), {})
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, roles), refresh_token=new_refresh)


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "status": user.status,
        "roles": [role.name for role in user.roles],
    }
