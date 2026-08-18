from sqlalchemy.orm import Session
from parentmanager.models import Parent
from parentmanager.schemas import ParentSignup


def create_parent(db: Session, payload: ParentSignup) -> Parent:
    parent = Parent(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        preferred_language=payload.preferred_language,
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
        relation=payload.relation,
        family_name_for_kids=payload.family_name_for_kids,
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def get_parent_by_id(db: Session, parent_id: int) -> Parent | None:
    return db.query(Parent).filter(Parent.id == parent_id).first()


def get_parent_by_email(db: Session, email: str) -> Parent | None:
    return db.query(Parent).filter(Parent.email == email).first()


def update_parent(db: Session, parent: Parent, data: dict) -> Parent:
    for field, value in data.items():
        setattr(parent, field, value)
    db.commit()
    db.refresh(parent)
    return parent

# no delete_parent: every field on this model is editable, so a parent
# who wants "gone" is served by clearing/editing fields, not row deletion.
# actual account deactivation/removal is a session/security-manager concern
# (kills sessions, revokes tokens) not a parentmanager data concern.
