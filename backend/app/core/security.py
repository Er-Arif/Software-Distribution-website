from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: UUID, roles: list[str]) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_minutes)).timestamp()),
        "jti": token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: UUID) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_urlsafe(32),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), expires_at


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_license_key(prefix: str = "SW") -> str:
    parts = [token_urlsafe(5).upper().replace("_", "A").replace("-", "Z")[:5] for _ in range(4)]
    return f"{prefix}-{'-'.join(parts)}"
