import secrets
import hashlib
from datetime import datetime, timedelta, timezone

SHORT_TTL_DAYS = 7
LONG_TTL_DAYS = 90


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def compute_expiry(remember_me: bool) -> datetime:
    days = LONG_TTL_DAYS if remember_me else SHORT_TTL_DAYS
    return datetime.now(timezone.utc) + timedelta(days=days)


def is_session_valid(expires_at: datetime, revoked_at: datetime | None) -> bool:
    if revoked_at is not None:
        return False
    return expires_at > datetime.now(timezone.utc)
