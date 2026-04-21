from app.core.rate_limit import POLICIES
from app.core.signing import sign_payload
from app.schemas import FingerprintInput
from app.services.licensing import fingerprint_hash


def test_rate_limit_categories_are_distinct():
    assert POLICIES["auth"].max_requests < POLICIES["license"].max_requests
    assert POLICIES["download"].max_requests < POLICIES["public"].max_requests


def test_fingerprint_hash_is_stable():
    payload = FingerprintInput(os="windows", app_installation_id="install-1", machine_id="machine-1")
    assert fingerprint_hash(payload) == fingerprint_hash(payload)


def test_signed_payload_contains_replay_fields():
    signed = sign_payload({"valid": True}, expires_in_seconds=60)
    assert signed["payload"]["nonce"]
    assert signed["payload"]["exp"] > signed["payload"]["iat"]
    assert signed["signature"]
    assert signed["public_key_id"]
