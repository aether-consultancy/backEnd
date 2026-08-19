from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from frontendmanager.eduWay import crud
from frontendmanager.eduWay.schemas import ClaimPreviewOut, ClaimConfirmIn, ClaimConfirmOut, MoreInfoIn, MoreInfoOut, LoginResolveOut, LoginConfirmIn, LoginConfirmOut
from sessionmanager import crud as session_crud
from fastapi import Header
from kidsmanager.schemas import KidProfileOut
from securitymanager.logic import generate_owner_token, verify_owner_token
from kidsmanager import crud as kids_crud
from kidsmanager.schemas import KidProfileOut
from sessionmanager.deps import get_current_kid
from kidsmanager.logic import is_valid_age


router = APIRouter(prefix="/frontend/kid", tags=["frontend-kid"])


@router.get("/claim/{claim_row_id}/{token}", response_model=ClaimPreviewOut)
def claim_preview(claim_row_id: int, token: str, db: Session = Depends(get_db)):
    kid, is_claimed = crud.preview_claim(db, claim_row_id, token)
    if kid is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")
    return ClaimPreviewOut(kid=kid, is_claimed=is_claimed)


@router.post("/claim/{claim_row_id}/{token}/confirm", response_model=ClaimConfirmOut)
def claim_confirm(claim_row_id: int, token: str, payload: ClaimConfirmIn, db: Session = Depends(get_db)):
    kid_id = crud.confirm_claim(db, claim_row_id, token, payload.password)
    if kid_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid, expired, or already-claimed code")

    proof_token, _ = generate_owner_token(kid_id)
    return ClaimConfirmOut(kid_id=kid_id, proof_token=proof_token)


@router.patch("/more-info", response_model=MoreInfoOut)
def more_info(payload: MoreInfoIn, db: Session = Depends(get_db)):
    kid_id = verify_owner_token(payload.proof_token)
    if kid_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired proof token")

    kid = kids_crud.get_kid_by_id_only(db, kid_id)
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")

    data = payload.model_dump(exclude_unset=True, exclude={"remember_me", "device_info", "proof_token"})
    if "age" in data and not is_valid_age(data["age"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Age out of allowed range")

    info, token, record = crud.submit_more_info(db, kid, data, payload.remember_me, payload.device_info)
    profile = KidProfileOut(
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
    return MoreInfoOut(kid=profile, token=token, expires_at=record.expires_at.isoformat())


@router.post("/login/{login_row_id}/{token}/resolve", response_model=LoginResolveOut)
def login_resolve(login_row_id: int, token: str, db: Session = Depends(get_db)):
    kid = crud.resolve_login(db, login_row_id, token)
    if kid is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")
    return LoginResolveOut(kid=kid)


@router.post("/login/confirm", response_model=LoginConfirmOut)
def login_confirm(payload: LoginConfirmIn, db: Session = Depends(get_db)):
    kid, token, record = crud.confirm_login(db, payload.kid_id, payload.password, payload.remember_me, payload.device_info)
    if kid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return LoginConfirmOut(kid=kid, token=token, expires_at=record.expires_at.isoformat())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    record = session_crud.logout(db, token)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already revoked session")

@router.get("/dashboard", response_model=KidProfileOut)
def dashboard(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    result = crud.get_dashboard(db, kid.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    kid_row, info = result
    return KidProfileOut(
        id=kid_row.id,
        full_name=kid_row.full_name,
        school=kid_row.school,
        grade=kid_row.grade,
        learning_system=kid_row.learning_system,
        nickname=info.nickname if info else None,
        age=info.age if info else None,
        favorite_color=info.favorite_color if info else None,
        favorite_animal=info.favorite_animal if info else None,
        subjects_loved=info.subjects_loved if info else None,
    )

