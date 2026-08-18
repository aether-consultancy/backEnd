import os
import hmac
import hashlib
import base64
import secrets
from datetime import datetime, timedelta, timezone

TOKEN_SECRET = os.getenv("TOKEN_SECRET", "change-me").encode()
TOKEN_TTL_MINUTES = 15


def _sign(payload: bytes) -> str:
    sig = hmac.new(TOKEN_SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_kid_token(kid_id: int) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    nonce = secrets.token_hex(8)
    payload = f"{kid_id}:{int(expires_at.timestamp())}:{nonce}".encode()
    signature = _sign(payload)
    token = f"{_b64encode(payload)}.{signature}"
    return token, expires_at


def verify_kid_token(token: str) -> int | None:
    try:
        payload_b64, signature = token.split(".")
        payload = _b64decode(payload_b64)
        expected_signature = _sign(payload)
        if not hmac.compare_digest(signature, expected_signature):
            return None

        kid_id_str, expires_str, _nonce = payload.decode().split(":")
        expires_at = datetime.fromtimestamp(int(expires_str), tz=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None

        return int(kid_id_str)
    except (ValueError, IndexError):
        return None


def is_token_used(used_at: datetime | None) -> bool:
    return used_at is not None
import secrets
import string

RESET_CODE_LENGTH = 6
RESET_CODE_TTL_MINUTES = 15
RESET_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_reset_code() -> str:
    return "".join(secrets.choice(RESET_CODE_ALPHABET) for _ in range(RESET_CODE_LENGTH))


# ---------- generic owner token ----------
# generalizes generate_kid_token/verify_kid_token below to any owner_id,
# not just kid_id. used by confirmationmanager's flow to prove "this
# request came right after a successful code verification" without a
# DB row (short TTL, no used_at tracking needed — single-shot proof,
# not a claim).

def generate_owner_token(owner_id: int) -> tuple[str, datetime]:
    return generate_kid_token(owner_id)


def verify_owner_token(token: str) -> int | None:
    return verify_kid_token(token)


# ---------- password hashing ----------
# moved here from the deleted app/security/hashing.py — this is the
# natural home per the manager architecture (securitymanager owns all
# password hashes). re-exported below for router.py/crud.py callers.

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
