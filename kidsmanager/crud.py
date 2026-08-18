from sqlalchemy.orm import Session
from kidsmanager.models import Kid, KidInfo
from kidsmanager.schemas import KidCreate


def create_kid(db: Session, parent_id: int, payload: KidCreate) -> Kid:
    kid = Kid(
        parent_id=parent_id,
        full_name=payload.full_name,
        school=payload.school,
        grade=payload.grade,
        learning_system=payload.learning_system,
    )
    db.add(kid)
    db.commit()
    db.refresh(kid)
    return kid


def get_kid_by_id_only(db: Session, kid_id: int) -> Kid | None:
    return db.query(Kid).filter(Kid.id == kid_id).first()


def get_kid_by_id(db: Session, kid_id: int, parent_id: int) -> Kid | None:
    return db.query(Kid).filter(Kid.id == kid_id, Kid.parent_id == parent_id).first()


def list_kids_by_parent(db: Session, parent_id: int) -> list[Kid]:
    return db.query(Kid).filter(Kid.parent_id == parent_id).order_by(Kid.created_at.asc()).all()


def get_kid_names_by_parent(db: Session, parent_id: int) -> list[str]:
    return [k.full_name for k in db.query(Kid).filter(Kid.parent_id == parent_id).all()]


def get_kid_info(db: Session, kid_id: int) -> KidInfo | None:
    return db.query(KidInfo).filter(KidInfo.kid_id == kid_id).first()


def update_kid_info(db: Session, kid_id: int, data: dict) -> KidInfo:
    info = get_kid_info(db, kid_id)
    if not info:
        info = KidInfo(kid_id=kid_id)
        db.add(info)

    for field, value in data.items():
        setattr(info, field, value)

    db.commit()
    db.refresh(info)
    return info


# ---------- delete ----------
# last-resort action, parent-only: removes the Kid row and its KidInfo
# row. Does NOT touch securitymanager's tables (KidPassword, claim/login
# tokens, reset codes) — that cleanup is securitymanager's job, called
# from router.py alongside this, to keep one-manager-one-job intact.

def delete_kid(db: Session, kid_id: int, parent_id: int) -> bool:
    kid = get_kid_by_id(db, kid_id, parent_id)
    if not kid:
        return False

    info = get_kid_info(db, kid_id)
    if info:
        db.delete(info)

    db.delete(kid)
    db.commit()
    return True


def update_kid(db: Session, kid: Kid, data: dict) -> Kid:
    for field, value in data.items():
        setattr(kid, field, value)
    db.commit()
    db.refresh(kid)
    return kid
