from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone

from sessionmanager.models import Session
from sessionmanager.logic import generate_session_token, hash_token, compute_expiry, is_session_valid


def issue_session(db: DBSession, owner_type: str, owner_id: int, remember_me: bool, device_info: str | None = None) -> tuple[str, Session]:
    token = generate_session_token()
    record = Session(
        owner_type=owner_type,
        owner_id=owner_id,
        token_hash=hash_token(token),
        remember_me=remember_me,
        device_info=device_info,
        expires_at=compute_expiry(remember_me),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return token, record


def validate_session(db: DBSession, token: str) -> Session | None:
    record = db.query(Session).filter(Session.token_hash == hash_token(token)).first()
    if not record or not is_session_valid(record.expires_at, record.revoked_at):
        return None

    record.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return record


def logout(db: DBSession, token: str) -> Session | None:
    record = db.query(Session).filter(Session.token_hash == hash_token(token)).first()
    if not record or record.revoked_at is not None:
        return None

    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return record


# ---------- logout all devices ----------
# called by frontendmanager: parent-triggered, cascades to the parent's
# own sessions AND every kid session under them. kid_ids passed in by
# the caller (frontendmanager pulls them from kidsmanager first) —
# sessionmanager does not import kidsmanager directly, keeps the
# one-manager-one-job boundary intact.

def logout_all_devices(db: DBSession, parent_id: int, kid_ids: list[int]) -> int:
    now = datetime.now(timezone.utc)

    parent_sessions = db.query(Session).filter(
        Session.owner_type == "parent",
        Session.owner_id == parent_id,
        Session.revoked_at.is_(None),
    ).all()

    kid_sessions = db.query(Session).filter(
        Session.owner_type == "kid",
        Session.owner_id.in_(kid_ids),
        Session.revoked_at.is_(None),
    ).all() if kid_ids else []

    for record in parent_sessions + kid_sessions:
        record.revoked_at = now

    db.commit()
    return len(parent_sessions) + len(kid_sessions)
