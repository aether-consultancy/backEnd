from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from confirmationmanager import crud
from confirmationmanager.schemas import VerificationCodeVerify, VerificationStatusOut
from securitymanager.logic import generate_owner_token

router = APIRouter(prefix="/confirmation", tags=["confirmation"])


@router.post("/parent/{verification_id}/verify")
def verify(verification_id: int, payload: VerificationCodeVerify, db: Session = Depends(get_db)):
    parent_id = crud.verify_email_code(db, verification_id, payload.code)
    if parent_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")

    proof_token, _ = generate_owner_token(parent_id)
    return {"parent_id": parent_id, "status": "verified", "proof_token": proof_token}


@router.get("/parent/{parent_id}/status", response_model=VerificationStatusOut)
def verification_status(parent_id: int, db: Session = Depends(get_db)):
    return VerificationStatusOut(parent_id=parent_id, verified=crud.is_email_verified(db, parent_id))
