from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dbmanager.connection import get_db
from parentmanager import crud
from parentmanager.schemas import ParentSignup, ParentOut
from parentmanager.logic import is_valid_phone, is_valid_password, normalize_phone
from securitymanager import crud as security_crud

router = APIRouter(prefix="/parent", tags=["parent"])

from sessionmanager.deps import get_current_parent
from parentmanager.models import Parent


# STALE: superseded by frontendmanager/eduParent /frontend/parent/signup
# (adds atomic rollback + verification email). Kept until that route is
# proven out, then comment/delete this one.
@router.post("/signup", response_model=ParentOut, status_code=status.HTTP_201_CREATED)
def signup(payload: ParentSignup, db: Session = Depends(get_db)):
    if not payload.terms_accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Terms must be accepted")
    if not is_valid_phone(payload.phone):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone must include country code")
    if not is_valid_password(payload.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too weak")
    if crud.get_parent_by_email(db, payload.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    payload.phone = normalize_phone(payload.phone)
    parent = crud.create_parent(db, payload)
    security_crud.create_parent_password(db, parent.id, payload.password)
    return parent


@router.get("/profile", response_model=ParentOut)
def profile(parent: Parent = Depends(get_current_parent)):
    return parent


class ParentEdit(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    relation: str | None = None
    family_name_for_kids: str | None = None


@router.patch("/profile", response_model=ParentOut)
def edit_profile(
    payload: ParentEdit,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    data = payload.model_dump(exclude_unset=True)
    if "phone" in data:
        if not is_valid_phone(data["phone"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone must include country code")
        data["phone"] = normalize_phone(data["phone"])
    return crud.update_parent(db, parent, data)
