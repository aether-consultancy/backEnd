from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dbmanager.connection import get_db
from securitymanager import crud
from securitymanager.schemas import KidTokenOut, ClaimConfirm, KidLoginConfirm, ResetCodeOut, ResetCodeVerify, ResetPasswordSet
from securitymanager.crud import hash_password
from securitymanager.models import KidPassword, KidClaimToken

router = APIRouter(prefix="/security", tags=["security"])

from sessionmanager.deps import get_current_parent, get_current_kid
from parentmanager.models import Parent


class PasswordCreate(BaseModel):
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.patch("/parent/password")
def change_parent_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    if not crud.verify_parent_password(db, parent.id, payload.current_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password incorrect")
    record = crud.get_parent_password(db, parent.id)
    record.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "updated"}


@router.patch("/kid/password")
def change_kid_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    kid=Depends(get_current_kid),
):
    if not crud.verify_kid_password(db, kid.id, payload.current_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password incorrect")
    record = crud.get_kid_password(db, kid.id)
    record.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "updated"}


@router.post("/kids/{kid_id}/claim-token", response_model=KidTokenOut)
def create_claim_token(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    token, record = crud.create_claim_token(db, kid_id)
    return KidTokenOut(row_id=record.id, token=token, expires_at=record.expires_at.isoformat())


@router.get("/kids/{kid_id}/claim-token/status")
def claim_token_status(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    claimed = crud.get_kid_password(db, kid_id) is not None
    return {"kid_id": kid_id, "claimed": claimed}


# STALE: superseded by frontendmanager/eduWay
# GET  /frontend/kid/claim/{claim_row_id}/{token}
# POST /frontend/kid/claim/{claim_row_id}/{token}/confirm
# (adds proof_token issuance for the more-info step). Kept until that
# route is proven out, then delete this pair.
# @router.get("/kids/claim/{claim_row_id}/{token}")
# def preview_claim(claim_row_id: int, token: str, db: Session = Depends(get_db)):
#     kid_id = crud.resolve_claim_token(db, token, claim_row_id)
#     if kid_id is None:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")
#     return {"kid_id": kid_id}
#
#
# @router.post("/kids/claim/{claim_row_id}/{token}/confirm")
# def confirm_claim(claim_row_id: int, token: str, payload: ClaimConfirm, db: Session = Depends(get_db)):
#     kid_id = crud.resolve_claim_token(db, token, claim_row_id)
#     if kid_id is None:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")
#     if crud.get_kid_password(db, kid_id):
#         raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kid already claimed")
#
#     crud.create_kid_password(db, kid_id, payload.password)
#     crud.mark_claim_token_used(db, claim_row_id)
#     return {"kid_id": kid_id, "status": "claimed"}


@router.post("/kids/{kid_id}/login-token", response_model=KidTokenOut)
def create_login_token(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    token, record = crud.create_login_token(db, kid_id)
    return KidTokenOut(row_id=record.id, token=token, expires_at=record.expires_at.isoformat())


@router.post("/kids/login/{login_row_id}/{token}/resolve")
def resolve_login(login_row_id: int, token: str, db: Session = Depends(get_db)):
    kid_id = crud.resolve_login_token(db, token, login_row_id)
    if kid_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")
    crud.mark_login_token_used(db, login_row_id)
    return {"kid_id": kid_id}


@router.post("/kids/login/confirm")
def confirm_login(kid_id: int, payload: KidLoginConfirm, db: Session = Depends(get_db)):
    if not crud.verify_kid_password(db, kid_id, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return {"kid_id": kid_id, "status": "verified"}


# ---------- parent forgot password ----------
# NOTE: gated by confirmationmanager ("is this email verified?") before
# this route is even reached — placeholder dependency for now.

@router.post("/parent/forgot-password", response_model=ResetCodeOut)
def request_parent_reset(parent_id: int, db: Session = Depends(get_db)):
    code, record = crud.create_parent_reset_code(db, parent_id)
    # confirmationmanager sends `code` via Brevo — not securitymanager's job
    return ResetCodeOut(reset_id=record.id, expires_at=record.expires_at.isoformat())


@router.post("/parent/forgot-password/{reset_id}/verify")
def verify_parent_reset(reset_id: int, payload: ResetCodeVerify, db: Session = Depends(get_db)):
    parent_id = crud.verify_parent_reset_code(db, reset_id, payload.code)
    if parent_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    return {"status": "verified"}


@router.post("/parent/forgot-password/{reset_id}/set-password")
def set_parent_new_password(reset_id: int, payload: ResetPasswordSet, db: Session = Depends(get_db)):
    ok = crud.consume_parent_reset_code(db, reset_id, payload.new_password)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code not verified or already used")
    return {"status": "password_reset"}


# ---------- kid forgot password ----------

@router.post("/kids/{kid_id}/forgot-password", response_model=ResetCodeOut)
def request_kid_reset(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    code, record = crud.create_kid_reset_code(db, kid_id)
    # code is shown directly in parent's app, not sent anywhere
    return ResetCodeOut(reset_id=record.id, expires_at=record.expires_at.isoformat())


@router.post("/kids/forgot-password/{reset_id}/verify")
def verify_kid_reset(reset_id: int, payload: ResetCodeVerify, db: Session = Depends(get_db)):
    kid_id = crud.verify_kid_reset_code(db, reset_id, payload.code)
    if kid_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    return {"kid_id": kid_id, "status": "verified"}


@router.post("/kids/forgot-password/{reset_id}/set-password")
def set_kid_new_password(reset_id: int, payload: ResetPasswordSet, db: Session = Depends(get_db)):
    ok = crud.consume_kid_reset_code(db, reset_id, payload.new_password)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code not verified or already used")
    return {"status": "password_reset"}


@router.delete("/kids/{kid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kid_security_data(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    crud.delete_kid_security_data(db, kid_id)
