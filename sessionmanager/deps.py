from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session as DBSession

from dbmanager.connection import get_db
from sessionmanager import crud
from parentmanager.crud import get_parent_by_id
from kidsmanager.crud import get_kid_by_id_only


def _extract_token(authorization: str) -> str:
    return authorization.removeprefix("Bearer ").strip()


def get_current_parent(authorization: str = Header(...), db: DBSession = Depends(get_db)):
    token = _extract_token(authorization)
    record = crud.validate_session(db, token)
    if not record or record.owner_type != "parent":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    parent = get_parent_by_id(db, record.owner_id)
    if not parent:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return parent


def get_current_kid(authorization: str = Header(...), db: DBSession = Depends(get_db)):
    token = _extract_token(authorization)
    record = crud.validate_session(db, token)
    if not record or record.owner_type != "kid":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    kid = get_kid_by_id_only(db, record.owner_id)
    if not kid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return kid
