from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from confirmationmanager.models import EmailVerificationCode
from confirmationmanager.logic import generate_verification_code, VERIFICATION_CODE_TTL_MINUTES, send_code_email
from securitymanager.crud import hash_password, verify_password
from parentmanager.crud import get_parent_by_id, update_parent


def create_verification_code(db: Session, parent_id: int, email: str) -> EmailVerificationCode:
    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES)
    record = EmailVerificationCode(parent_id=parent_id, code_hash=hash_password(code), expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)

    send_code_email(email, code, purpose="verification")
    return record


def verify_email_code(db: Session, verification_id: int, code: str) -> int | None:
    record = db.query(EmailVerificationCode).filter(EmailVerificationCode.id == verification_id).first()
    if not record or record.used_at is not None or record.expires_at < datetime.now(timezone.utc):
        return None
    if not verify_password(code, record.code_hash):
        return None

    record.used_at = datetime.now(timezone.utc)
    db.commit()

    parent = get_parent_by_id(db, record.parent_id)
    if parent:
        update_parent(db, parent, {"email_verified": True})

    return record.parent_id


def is_email_verified(db: Session, parent_id: int) -> bool:
    parent = get_parent_by_id(db, parent_id)
    return bool(parent and parent.email_verified)


# called by securitymanager's forgot-password flow to send the code —
# securitymanager generates/stores it, confirmationmanager just delivers it.
def send_reset_code_email(email: str, code: str) -> bool:
    return send_code_email(email, code, purpose="reset")
