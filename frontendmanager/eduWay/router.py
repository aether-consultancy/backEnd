from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from frontendmanager.eduWay import crud
from frontendmanager.eduWay.schemas import ClaimPreviewOut, ClaimConfirmIn, ClaimConfirmOut, MoreInfoIn, MoreInfoOut, LoginResolveOut, LoginConfirmIn, LoginConfirmOut, ResetPasswordVerifyIn, ResetPasswordVerifyOut, ResetPasswordSetIn, ResetPasswordSetOut, GameHomeOut, KidDashboardOut, SubjectTeacherAssignIn
from sessionmanager import crud as session_crud
from fastapi import Header
from kidsmanager.schemas import KidProfileOut
from securitymanager.logic import generate_owner_token, verify_owner_token
from kidsmanager import crud as kids_crud
from kidsmanager.schemas import KidProfileOut
from sessionmanager.deps import get_current_kid
from kidsmanager.logic import is_valid_age
from gamemanager.schemas import WalletOut, NextLevelsOut, GameLevelOut, SlotSolveIn, SlotSolveOut, LevelCompleteIn, LevelCompleteOut, LeaderboardEntryOut


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

@router.get("/dashboard", response_model=KidDashboardOut)
def dashboard(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    result = crud.get_dashboard(db, kid.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    kid_row, info, activated, setup_complete, subjects, teachers = result
    return KidDashboardOut(
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
        school_activated=activated,
        school_setup_complete=setup_complete,
        subjects=subjects,
        teachers=teachers,
    )


@router.patch("/school/subjects/{subject_id}/teacher")
def assign_subject_teacher(subject_id: int, payload: SubjectTeacherAssignIn, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    subject = crud.assign_subject_teacher(db, kid.id, subject_id, payload.teacher_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject or teacher not found")
    return subject



# ---------- reset password (kid side) ----------

@router.get("/game/home", response_model=GameHomeOut)
def frontend_game_home(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    wallet, current_level, levels, progress, streak_active = crud.get_game_home(db, kid.id)
    return GameHomeOut(
        wallet=wallet,
        current_level=current_level,
        levels=[GameLevelOut.model_validate(l) for l in levels],
        current_streak=progress.current_streak,
        longest_streak=progress.longest_streak,
        streak_active=streak_active,
    )


@router.get("/game/leaderboard", response_model=list[LeaderboardEntryOut])
def frontend_leaderboard(limit: int = 50, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.get_leaderboard(db, limit=limit)


@router.post("/game/crossword/slot-solved", response_model=SlotSolveOut)
def frontend_slot_solved(payload: SlotSolveIn, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    result = crud.report_slot_solved(db, kid.id, payload.level_id, payload.slot_number)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    awarded, bonus_coins, wallet, xp_awarded = result
    return SlotSolveOut(
        bonus_awarded=awarded, bonus_coins=bonus_coins,
        wallet_coins=wallet.coins, wallet_keys=wallet.keys,
        xp_awarded=xp_awarded,
    )


@router.post("/game/crossword/complete", response_model=LevelCompleteOut)
def frontend_level_complete(payload: LevelCompleteIn, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    result = crud.report_level_complete(db, kid.id, payload.level_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    level, wallet, progress, xp_awarded = result
    return LevelCompleteOut(
        coins_awarded=level.completion_reward,
        wallet_coins=wallet.coins, wallet_keys=wallet.keys,
        current_level=progress.current_level,
        xp_awarded=xp_awarded,
    )


@router.get("/game/wallet", response_model=WalletOut)
def frontend_game_wallet(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.get_wallet(db, kid.id)


@router.get("/game/crossword/next", response_model=NextLevelsOut)
def frontend_next_crossword_levels(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    current_level, levels = crud.get_next_crossword_levels(db, kid.id)
    return NextLevelsOut(current_level=current_level, levels=[GameLevelOut.model_validate(l) for l in levels])


@router.post("/reset-password/verify", response_model=ResetPasswordVerifyOut)
def verify_reset_password(payload: ResetPasswordVerifyIn, db: Session = Depends(get_db)):
    ok = crud.verify_reset_code(db, payload.kid_id, payload.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    proof_token, _ = generate_owner_token(payload.kid_id)
    return ResetPasswordVerifyOut(proof_token=proof_token)


@router.post("/reset-password/set", response_model=ResetPasswordSetOut)
def set_reset_password(payload: ResetPasswordSetIn, db: Session = Depends(get_db)):
    kid_id = verify_owner_token(payload.proof_token)
    if kid_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    ok = crud.set_new_password(db, kid_id, payload.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Reset not verified")
    return ResetPasswordSetOut(status="password_reset")

from schoolmanager import schemas as school_schemas


@router.get("/subjects", response_model=list[school_schemas.SubjectOut])
def list_subjects_kid(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.list_subjects(db, kid.id)


@router.patch("/subjects/{subject_id}", response_model=school_schemas.SubjectOut)
def update_subject_kid(subject_id: int, payload: school_schemas.SubjectUpdate, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    subject = crud.update_subject(db, kid.id, subject_id, payload.name)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")
    return subject


@router.get("/teachers", response_model=list[school_schemas.TeacherOut])
def list_teachers_kid(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.list_teachers(db, kid.id)


@router.patch("/teachers/{teacher_id}", response_model=school_schemas.TeacherOut)
def update_teacher_kid(teacher_id: int, payload: school_schemas.TeacherUpdate, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    try:
        teacher = crud.update_teacher(db, kid.id, teacher_id, payload.name, payload.phone, payload.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher not found")
    return teacher
