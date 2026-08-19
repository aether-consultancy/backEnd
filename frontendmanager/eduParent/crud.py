from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from parentmanager.schemas import ParentSignup
from parentmanager.models import Parent
from parentmanager import crud as parent_crud
from securitymanager import crud as security_crud
from confirmationmanager import crud as confirmation_crud
from confirmationmanager.models import EmailVerificationCode
from sessionmanager import crud as session_crud
from kidsmanager import crud as kids_crud
from kidsmanager.models import Kid, KidInfo


# ---------- signup ----------
# atomic: parent + password succeed together or not at all.
# verification email is best-effort AFTER that succeeds — a failed
# send never rolls back an already-valid account+password.

def signup_parent(db: Session, payload: ParentSignup) -> tuple[Parent, EmailVerificationCode]:
    parent = parent_crud.create_parent(db, payload)

    try:
        security_crud.create_parent_password(db, parent.id, payload.password)
    except Exception:
        db.delete(parent)
        db.commit()
        raise

    verification = confirmation_crud.create_verification_code(db, parent.id, parent.email)
    return parent, verification


# ---------- more-info + session issuance ----------
# called once, right after email confirm — fills remaining profile
# fields and issues the session in one shot. no atomicity concern here:
# update_parent and issue_session are independent writes, either can
# succeed alone without corrupting state (a filled profile with no
# session just means the FE retries session issuance, not a rollback).

def submit_more_info(db: Session, parent: Parent, data: dict, remember_me: bool, device_info: str | None):
    try:
        updated = parent_crud.update_parent(db, parent, data)
    except IntegrityError:
        db.rollback()
        raise ValueError("Phone number already in use by another account")
    updated.onboarding_completed = True
    db.commit()
    db.refresh(updated)
    token, record = session_crud.issue_session(db, "parent", updated.id, remember_me, device_info)
    return updated, token, record


# ---------- login ----------
# resolves email -> parent_id (FE only has email), verifies password,
# issues a session. single call, no multi-step needed unlike signup.

def login_parent(db: Session, email: str, password: str, remember_me: bool, device_info: str | None):
    parent = parent_crud.get_parent_by_email(db, email)
    if not parent:
        return None, None, None
    if not security_crud.verify_parent_password(db, parent.id, password):
        return None, None, None

    token, record = session_crud.issue_session(db, "parent", parent.id, remember_me, device_info)
    return parent, token, record


# ---------- logout all devices ----------
# cascades to every kid under this parent — pulls kid_ids here since
# sessionmanager deliberately doesn't import kidsmanager (one-manager-
# one-job boundary).

def logout_all_devices(db: Session, parent_id: int) -> int:
    kid_ids = [k.id for k in kids_crud.list_kids_by_parent(db, parent_id)]
    return session_crud.logout_all_devices(db, parent_id, kid_ids)

# ---------- kid list + profile (parent-facing) ----------
# parent app never calls kidsmanager or securitymanager directly — these
# aggregate both into the shapes the FE actually needs.

def list_kids(db: Session, parent_id: int) -> list[Kid]:
    return kids_crud.list_kids_by_parent(db, parent_id)


def get_kid_profile(db: Session, kid_id: int, parent_id: int):
    kid = kids_crud.get_kid_by_id(db, kid_id, parent_id)
    if not kid:
        return None

    info = kids_crud.get_kid_info(db, kid_id)
    claimed = security_crud.get_kid_password(db, kid_id) is not None

    return {
        "id": kid.id,
        "full_name": kid.full_name,
        "school": kid.school,
        "grade": kid.grade,
        "learning_system": kid.learning_system,
        "nickname": info.nickname if info else None,
        "age": info.age if info else None,
        "favorite_color": info.favorite_color if info else None,
        "favorite_animal": info.favorite_animal if info else None,
        "subjects_loved": info.subjects_loved if info else None,
        "claimed": claimed,
    }

# ---------- dashboard ----------
# aggregates parent profile + kid list in one call — the whole point of
# a facade route, vs the FE hitting /parent/profile and /kids
# separately against two different managers.

def get_dashboard(db: Session, parent: Parent):
    kids = kids_crud.list_kids_by_parent(db, parent.id)
    return parent, kids

