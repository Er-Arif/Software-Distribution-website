import base64
import hmac
import struct
from hashlib import sha1, sha256
from secrets import token_urlsafe
from time import time
from urllib.parse import quote

from app.core.config import settings


def generate_totp_secret() -> str:
    return base64.b32encode(token_urlsafe(20).encode("utf-8")).decode("ascii").rstrip("=")


def recovery_code_hash(code: str) -> str:
    return sha256(code.encode("utf-8")).hexdigest()


def generate_recovery_codes(count: int = 8) -> tuple[list[str], list[str]]:
    codes = [token_urlsafe(9).replace("-", "").replace("_", "")[:12].upper() for _ in range(count)]
    return codes, [recovery_code_hash(code) for code in codes]


def provisioning_uri(email: str, secret: str) -> str:
    issuer = quote(settings.admin_2fa_issuer)
    label = quote(f"{settings.admin_2fa_issuer}:{email}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def _hotp(secret: str, counter: int) -> str:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded.encode("ascii"), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def verify_totp(secret: str, code: str, drift_windows: int = 1) -> bool:
    if not secret or not code or not code.isdigit():
        return False
    counter = int(time() // 30)
    for offset in range(-drift_windows, drift_windows + 1):
        if hmac.compare_digest(_hotp(secret, counter + offset), code):
            return True
    return False
