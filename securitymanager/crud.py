from sqlalchemy.orm import Session
from datetime import datetime, timezone

from securitymanager.models import ParentPassword, KidPassword, KidClaimToken, KidLoginToken, ParentResetCode, KidResetCode
from securitymanager.logic import generate_kid_token, verify_kid_token, is_token_used
from securitymanager.logic import hash_password, verify_password  # re-exported for router.py


# ---------- parent password ----------

def create_parent_password(db: Session, parent_id: int, password: str) -> ParentPassword:
    record = ParentPassword(parent_id=parent_id, password_hash=hash_password(password))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_parent_password(db: Session, parent_id: int) -> ParentPassword | None:
    return db.query(ParentPassword).filter(ParentPassword.parent_id == parent_id).first()


def verify_parent_password(db: Session, parent_id: int, password: str) -> bool:
    record = get_parent_password(db, parent_id)
    if not record:
        return False
    return verify_password(password, record.password_hash)


# ---------- kid password ----------

def create_kid_password(db: Session, kid_id: int, password: str) -> KidPassword:
    record = KidPassword(kid_id=kid_id, password_hash=hash_password(password))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_kid_password(db: Session, kid_id: int) -> KidPassword | None:
    return db.query(KidPassword).filter(KidPassword.kid_id == kid_id).first()


def verify_kid_password(db: Session, kid_id: int, password: str) -> bool:
    record = get_kid_password(db, kid_id)
    if not record:
        return False
    return verify_password(password, record.password_hash)


# ---------- kid claim token (signup/QR provisioning) ----------

def create_claim_token(db: Session, kid_id: int) -> tuple[str, KidClaimToken]:
    token, expires_at = generate_kid_token(kid_id)
    record = KidClaimToken(kid_id=kid_id, expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return token, record


def resolve_claim_token(db: Session, token: str, claim_row_id: int) -> int | None:
    kid_id = verify_kid_token(token)
    if kid_id is None:
        return None

    record = db.query(KidClaimToken).filter(KidClaimToken.id == claim_row_id).first()
    if not record or is_token_used(record.used_at) or record.expires_at < datetime.now(timezone.utc):
        return None

    return kid_id


def mark_claim_token_used(db: Session, claim_row_id: int) -> None:
    record = db.query(KidClaimToken).filter(KidClaimToken.id == claim_row_id).first()
    if record:
        record.used_at = datetime.now(timezone.utc)
        db.commit()


# ---------- kid login token (QR login) ----------

def create_login_token(db: Session, kid_id: int) -> tuple[str, KidLoginToken]:
    token, expires_at = generate_kid_token(kid_id)
    record = KidLoginToken(kid_id=kid_id, expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return token, record


def resolve_login_token(db: Session, token: str, login_row_id: int) -> int | None:
    kid_id = verify_kid_token(token)
    if kid_id is None:
        return None

    record = db.query(KidLoginToken).filter(KidLoginToken.id == login_row_id).first()
    if not record or is_token_used(record.used_at) or record.expires_at < datetime.now(timezone.utc):
        return None

    return kid_id


def mark_login_token_used(db: Session, login_row_id: int) -> None:
    record = db.query(KidLoginToken).filter(KidLoginToken.id == login_row_id).first()
    if record:
        record.used_at = datetime.now(timezone.utc)
        db.commit()


# ---------- parent forgot password ----------

def create_parent_reset_code(db: Session, parent_id: int) -> tuple[str, ParentResetCode]:
    from securitymanager.logic import generate_reset_code, RESET_CODE_TTL_MINUTES
    from datetime import timedelta

    code = generate_reset_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    record = ParentResetCode(parent_id=parent_id, code_hash=hash_password(code), expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return code, record


def verify_parent_reset_code(db: Session, reset_row_id: int, code: str) -> int | None:
    record = db.query(ParentResetCode).filter(ParentResetCode.id == reset_row_id).first()
    if not record or is_token_used(record.used_at) or record.expires_at < datetime.now(timezone.utc):
        return None
    if not verify_password(code, record.code_hash):
        return None

    record.verified_at = datetime.now(timezone.utc)
    db.commit()
    return record.parent_id


def consume_parent_reset_code(db: Session, reset_row_id: int, new_password: str) -> bool:
    record = db.query(ParentResetCode).filter(ParentResetCode.id == reset_row_id).first()
    if not record or record.verified_at is None or is_token_used(record.used_at):
        return False

    existing = get_parent_password(db, record.parent_id)
    if existing:
        existing.password_hash = hash_password(new_password)
    else:
        db.add(ParentPassword(parent_id=record.parent_id, password_hash=hash_password(new_password)))

    record.used_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ---------- kid forgot password ----------

def create_kid_reset_code(db: Session, kid_id: int) -> tuple[str, KidResetCode]:
    from securitymanager.logic import generate_reset_code, RESET_CODE_TTL_MINUTES
    from datetime import timedelta

    code = generate_reset_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    record = KidResetCode(kid_id=kid_id, code_hash=hash_password(code), expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return code, record


def verify_kid_reset_code(db: Session, reset_row_id: int, code: str) -> int | None:
    record = db.query(KidResetCode).filter(KidResetCode.id == reset_row_id).first()
    if not record or is_token_used(record.used_at) or record.expires_at < datetime.now(timezone.utc):
        return None
    if not verify_password(code, record.code_hash):
        return None

    record.verified_at = datetime.now(timezone.utc)
    db.commit()
    return record.kid_id


def consume_kid_reset_code(db: Session, reset_row_id: int, new_password: str) -> bool:
    record = db.query(KidResetCode).filter(KidResetCode.id == reset_row_id).first()
    if not record or record.verified_at is None or is_token_used(record.used_at):
        return False

    existing = get_kid_password(db, record.kid_id)
    if existing:
        existing.password_hash = hash_password(new_password)
    else:
        db.add(KidPassword(kid_id=record.kid_id, password_hash=hash_password(new_password)))

    record.used_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ---------- kid deletion cleanup ----------
# called by frontendmanager alongside kidsmanager's own delete_kid,
# never directly by kidsmanager (one-manager-one-job).

def delete_kid_security_data(db: Session, kid_id: int) -> None:
    db.query(KidPassword).filter(KidPassword.kid_id == kid_id).delete()
    db.query(KidClaimToken).filter(KidClaimToken.kid_id == kid_id).delete()
    db.query(KidLoginToken).filter(KidLoginToken.kid_id == kid_id).delete()
    db.query(KidResetCode).filter(KidResetCode.kid_id == kid_id).delete()
    db.commit()


# ---------- kid forgot password (kid_id-keyed, for FE wrappers) ----------

def get_active_kid_reset_code(db: Session, kid_id: int) -> KidResetCode | None:
    return (
        db.query(KidResetCode)
        .filter(KidResetCode.kid_id == kid_id, KidResetCode.used_at.is_(None))
        .order_by(KidResetCode.id.desc())
        .first()
    )


def verify_kid_reset_code_by_kid(db: Session, kid_id: int, code: str) -> bool:
    record = get_active_kid_reset_code(db, kid_id)
    if not record or record.expires_at < datetime.now(timezone.utc):
        return False
    if not verify_password(code, record.code_hash):
        return False
    record.verified_at = datetime.now(timezone.utc)
    db.commit()
    return True


def consume_kid_reset_code_by_kid(db: Session, kid_id: int, new_password: str) -> bool:
    record = get_active_kid_reset_code(db, kid_id)
    if not record or record.verified_at is None:
        return False
    existing = get_kid_password(db, kid_id)
    if existing:
        existing.password_hash = hash_password(new_password)
    else:
        db.add(KidPassword(kid_id=kid_id, password_hash=hash_password(new_password)))
    record.used_at = datetime.now(timezone.utc)
    db.commit()
    return True
