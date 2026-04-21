import base64
import json
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from app.core.config import settings


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_or_create_private_key():
    if settings.license_private_key_pem:
        return serialization.load_pem_private_key(
            settings.license_private_key_pem.encode("utf-8"),
            password=None,
        )
    return ed25519.Ed25519PrivateKey.generate()


PRIVATE_KEY = _load_or_create_private_key()
PUBLIC_KEY = PRIVATE_KEY.public_key()


def public_key_pem() -> str:
    key = PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key.decode("utf-8")


def sign_payload(payload: dict[str, Any], expires_in_seconds: int = 900) -> dict[str, Any]:
    signed = {
        **payload,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(seconds=expires_in_seconds)).timestamp()),
        "nonce": token_urlsafe(18),
        "kid": settings.signing_key_id,
    }
    body = _canonical(signed)
    if isinstance(PRIVATE_KEY, ed25519.Ed25519PrivateKey):
        signature = PRIVATE_KEY.sign(body)
        alg = "EdDSA"
    elif isinstance(PRIVATE_KEY, rsa.RSAPrivateKey):
        signature = PRIVATE_KEY.sign(body, padding.PKCS1v15(), hashes.SHA256())
        alg = "RS256"
    else:
        raise RuntimeError("Unsupported signing key")
    return {
        "payload": signed,
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
        "algorithm": alg,
        "public_key_id": settings.signing_key_id,
    }


def verify_signed_payload(signed: dict[str, Any]) -> bool:
    payload = signed["payload"]
    signature = base64.urlsafe_b64decode(signed["signature"])
    body = _canonical(payload)
    if payload["exp"] < int(datetime.now(UTC).timestamp()):
        return False
    if signed["algorithm"] == "EdDSA":
        PUBLIC_KEY.verify(signature, body)
        return True
    if signed["algorithm"] == "RS256":
        PUBLIC_KEY.verify(signature, body, padding.PKCS1v15(), hashes.SHA256())
        return True
    return False
