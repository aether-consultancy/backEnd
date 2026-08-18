from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session as DBSession

from dbmanager.connection import get_db
from sessionmanager import crud

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str = Header(...), db: DBSession = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    record = crud.logout(db, token)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already revoked session")
