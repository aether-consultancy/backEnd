from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from kidsmanager import crud
from kidsmanager.schemas import KidCreate, KidOut, KidInfoUpdate, KidProfileOut, KidEdit
from kidsmanager.logic import is_valid_age, is_duplicate_kid_name

router = APIRouter(prefix="/kids", tags=["kids"])

from sessionmanager.deps import get_current_parent, get_current_kid
from parentmanager.models import Parent


@router.post("", response_model=KidOut, status_code=status.HTTP_201_CREATED)
def create_kid(payload: KidCreate, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    existing_names = crud.get_kid_names_by_parent(db, parent.id)
    if is_duplicate_kid_name(existing_names, payload.full_name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A scholar with this name already exists on your account")

    return crud.create_kid(db, parent.id, payload)


@router.get("", response_model=list[KidOut])
def list_kids(db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    return crud.list_kids_by_parent(db, parent.id)


@router.get("/{kid_id}", response_model=KidOut)
def get_kid(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    kid = crud.get_kid_by_id(db, kid_id, parent.id)
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return kid


@router.get("/me", response_model=KidProfileOut)
def get_my_profile(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    info = crud.get_kid_info(db, kid.id)
    return KidProfileOut(
        id=kid.id,
        full_name=kid.full_name,
        school=kid.school,
        grade=kid.grade,
        learning_system=kid.learning_system,
        nickname=info.nickname if info else None,
        age=info.age if info else None,
        favorite_color=info.favorite_color if info else None,
        favorite_animal=info.favorite_animal if info else None,
        subjects_loved=info.subjects_loved if info else None,
    )


@router.patch("/me", response_model=KidProfileOut)
def update_my_profile(payload: KidInfoUpdate, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    data = payload.model_dump(exclude_unset=True)
    if "age" in data and not is_valid_age(data["age"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Age out of allowed range")

    info = crud.update_kid_info(db, kid.id, data)
    return KidProfileOut(
        id=kid.id,
        full_name=kid.full_name,
        school=kid.school,
        grade=kid.grade,
        learning_system=kid.learning_system,
        nickname=info.nickname,
        age=info.age,
        favorite_color=info.favorite_color,
        favorite_animal=info.favorite_animal,
        subjects_loved=info.subjects_loved,
    )


@router.delete("/{kid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kid(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    deleted = crud.delete_kid(db, kid_id, parent.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")


@router.patch("/{kid_id}", response_model=KidOut)
def update_kid(kid_id: int, payload: KidEdit, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    kid = crud.get_kid_by_id(db, kid_id, parent.id)
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")

    data = payload.model_dump(exclude_unset=True)
    return crud.update_kid(db, kid, data)
