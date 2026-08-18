import re
from datetime import datetime, timedelta, timezone

PHONE_REGEX = re.compile(r"^\+[1-9][0-9]{7,14}$")
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-]", "", phone)


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_REGEX.match(phone))


def is_valid_password(password: str) -> bool:
    if len(password) < MIN_PASSWORD_LENGTH:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def is_locked_out(locked_until: datetime | None) -> bool:
    if not locked_until:
        return False
    return locked_until > datetime.now(timezone.utc)


def compute_lockout(failed_attempts: int) -> datetime | None:
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        return datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
    return None


def requires_email_verification(email_verified: bool) -> bool:
    return not email_verified
