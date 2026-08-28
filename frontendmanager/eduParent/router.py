from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from parentmanager.schemas import ParentSignup
from parentmanager.logic import is_valid_phone, is_valid_password, normalize_phone
from parentmanager import crud as parent_crud
from frontendmanager.eduParent import crud
from frontendmanager.eduParent.schemas import SignupOut, MoreInfoIn, MoreInfoOut, KidProfileWithStatusOut, DashboardOut, ResetKidPasswordOut
from kidsmanager.schemas import KidOut
from confirmationmanager import crud as confirmation_crud
from confirmationmanager.schemas import VerificationCodeVerify
from securitymanager.logic import generate_owner_token, verify_owner_token
from frontendmanager.eduParent.schemas import LoginIn, LoginOut, LogoutAllOut
from sessionmanager import crud as session_crud
from sessionmanager.deps import get_current_parent
from parentmanager.models import Parent
from fastapi import Header

router = APIRouter(prefix="/frontend/parent", tags=["frontend-parent"])


@router.post("/signup", response_model=SignupOut, status_code=status.HTTP_201_CREATED)
def signup(payload: ParentSignup, db: Session = Depends(get_db)):
    if not payload.terms_accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Terms must be accepted")
    if payload.phone is not None and not is_valid_phone(payload.phone):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone must include country code")
    if not is_valid_password(payload.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too weak")
    if parent_crud.get_parent_by_email(db, payload.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    if payload.phone is not None:
        payload.phone = normalize_phone(payload.phone)
    parent, verification = crud.signup_parent(db, payload)

    return SignupOut(
        parent=parent,
        verification_id=verification.id,
        verification_expires_at=verification.expires_at.isoformat(),
    )


@router.post("/confirm-email/{verification_id}")
def confirm_email(verification_id: int, payload: VerificationCodeVerify, db: Session = Depends(get_db)):
    parent_id = confirmation_crud.verify_email_code(db, verification_id, payload.code)
    if parent_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")

    proof_token, _ = generate_owner_token(parent_id)
    return {"parent_id": parent_id, "status": "verified", "proof_token": proof_token}


@router.patch("/more-info", response_model=MoreInfoOut)
def more_info(payload: MoreInfoIn, db: Session = Depends(get_db)):
    parent_id = verify_owner_token(payload.proof_token)
    if parent_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired proof token")

    parent = parent_crud.get_parent_by_id(db, parent_id)
    if not parent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent not found")

    data = payload.model_dump(exclude_unset=True, exclude={"remember_me", "device_info", "proof_token"})
    if "phone" in data:
        if not is_valid_phone(data["phone"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone must include country code")
        data["phone"] = normalize_phone(data["phone"])

    try:
        updated, token, record = crud.submit_more_info(db, parent, data, payload.remember_me, payload.device_info)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return MoreInfoOut(parent=updated, token=token, expires_at=record.expires_at.isoformat())


@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    parent, token, record = crud.login_parent(db, payload.email, payload.password, payload.remember_me, payload.device_info)
    if parent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return LoginOut(parent=parent, token=token, expires_at=record.expires_at.isoformat())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    record = session_crud.logout(db, token)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already revoked session")


@router.post("/logout-all", response_model=LogoutAllOut)
def logout_all(db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    revoked = crud.logout_all_devices(db, parent.id)
    return LogoutAllOut(sessions_revoked=revoked)

@router.get("/kids", response_model=list[KidOut])
def list_kids(db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    return crud.list_kids(db, parent.id)


@router.get("/kids/{kid_id}", response_model=KidProfileWithStatusOut)
def get_kid_profile(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    profile = crud.get_kid_profile(db, kid_id, parent.id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return KidProfileWithStatusOut(**profile)

@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    parent_row, kids = crud.get_dashboard(db, parent)
    return DashboardOut(parent=parent_row, kids=kids)



# ---------- reset kid password ----------

@router.post("/reset-kid-password/{kid_id}", response_model=ResetKidPasswordOut)
def reset_kid_password_ep(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    result = crud.reset_kid_password(db, kid_id, parent.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Kid not found")
    code, expires_at = result
    return ResetKidPasswordOut(code=code, expires_at=expires_at.isoformat())

from schoolmanager import schemas as school_schemas


@router.post("/kids/{kid_id}/subjects", response_model=school_schemas.SubjectOut)
def create_subject(kid_id: int, payload: school_schemas.SubjectCreate, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    try:
        subject = crud.create_subject(db, parent.id, kid_id, payload.name)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return subject


@router.get("/kids/{kid_id}/subjects", response_model=list[school_schemas.SubjectOut])
def list_subjects(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    subjects = crud.list_subjects(db, parent.id, kid_id)
    if subjects is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return subjects


@router.patch("/kids/{kid_id}/subjects/{subject_id}", response_model=school_schemas.SubjectOut)
def update_subject(kid_id: int, subject_id: int, payload: school_schemas.SubjectUpdate, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    subject = crud.update_subject(db, parent.id, kid_id, subject_id, payload.name)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid or subject not found")
    return subject


@router.delete("/kids/{kid_id}/subjects/{subject_id}")
def delete_subject(kid_id: int, subject_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    if not crud.delete_subject(db, parent.id, kid_id, subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid or subject not found")
    return {"deleted": True}


@router.post("/kids/{kid_id}/teachers", response_model=school_schemas.TeacherOut)
def create_teacher(kid_id: int, payload: school_schemas.TeacherCreate, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    try:
        teacher = crud.create_teacher(db, parent.id, kid_id, payload.name, payload.phone, payload.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return teacher


@router.get("/kids/{kid_id}/teachers", response_model=list[school_schemas.TeacherOut])
def list_teachers(kid_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    teachers = crud.list_teachers(db, parent.id, kid_id)
    if teachers is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    return teachers


@router.patch("/kids/{kid_id}/teachers/{teacher_id}", response_model=school_schemas.TeacherOut)
def update_teacher(kid_id: int, teacher_id: int, payload: school_schemas.TeacherUpdate, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    try:
        teacher = crud.update_teacher(db, parent.id, kid_id, teacher_id, payload.name, payload.phone, payload.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid or teacher not found")
    return teacher


@router.patch("/kids/{kid_id}/subjects/{subject_id}/favorite", response_model=school_schemas.SubjectOut)
def set_favorite_subject(kid_id: int, subject_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    subject = crud.set_favorite_subject(db, parent.id, kid_id, subject_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid or subject not found")
    return subject


@router.delete("/kids/{kid_id}/teachers/{teacher_id}")
def delete_teacher(kid_id: int, teacher_id: int, db: Session = Depends(get_db), parent: Parent = Depends(get_current_parent)):
    if not crud.delete_teacher(db, parent.id, kid_id, teacher_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid or teacher not found")
    return {"deleted": True}
