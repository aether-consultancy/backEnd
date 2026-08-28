from sqlalchemy.orm import Session

from kidsmanager.models import Kid
from kidsmanager import crud as kids_crud
from securitymanager import crud as security_crud
from sessionmanager import crud as session_crud
from gamemanager import crud as game_crud
from schoolmanager import crud as school_crud


def _attach_info(db: Session, kid: Kid) -> Kid:
    # KidOut reads attributes straight off the Kid ORM object, but
    # nickname/favorite_animal live on the separate KidInfo table -
    # stamp them on before returning so serialization picks them up.
    if kid is None:
        return kid
    info = kids_crud.get_kid_info(db, kid.id)
    kid.nickname = info.nickname if info else None
    kid.favorite_animal = info.favorite_animal if info else None
    return kid


# ---------- claim preview ----------
# read-only: validates the claim token without consuming it, fetches
# the kid record the parent already created so the kid app can show
# "is this you" before any password is set.

def preview_claim(db: Session, claim_row_id: int, token: str) -> tuple[Kid | None, bool]:
    kid_id = security_crud.resolve_claim_token(db, token, claim_row_id)
    if kid_id is None:
        return None, False

    kid = _attach_info(db, kids_crud.get_kid_by_id_only(db, kid_id))
    is_claimed = security_crud.get_kid_password(db, kid_id) is not None
    return kid, is_claimed


# ---------- claim confirm + set password ----------
# re-verifies the token (never trust a prior preview call), then sets
# the password and marks the token used. password write happens before
# marking used — if create_kid_password fails, the token stays valid
# and the claim is retryable instead of stranding the kid mid-claim.

def confirm_claim(db: Session, claim_row_id: int, token: str, password: str) -> int | None:
    kid_id = security_crud.resolve_claim_token(db, token, claim_row_id)
    if kid_id is None:
        return None
    if security_crud.get_kid_password(db, kid_id):
        return None

    security_crud.create_kid_password(db, kid_id, password)
    security_crud.mark_claim_token_used(db, claim_row_id)
    return kid_id


# ---------- more-info + session issuance ----------
# gated by proof_token from claim-confirm, same pattern as eduParent's
# EP3. kid has no session yet at this point — this is where one gets
# minted, with remember_me honored the same way parents get it.

def submit_more_info(db: Session, kid: Kid, data: dict, remember_me: bool, device_info: str | None):
    info = kids_crud.update_kid_info(db, kid.id, data)
    token, record = session_crud.issue_session(db, "kid", kid.id, remember_me, device_info)
    return info, token, record


# ---------- QR login: resolve ----------
# kills the token immediately at scan (matches the WhatsApp-Web-QR
# pattern) and returns the kid so the app can show "Hi {name}, enter
# your password" before any password is involved.

def resolve_login(db: Session, login_row_id: int, token: str) -> Kid | None:
    kid_id = security_crud.resolve_login_token(db, token, login_row_id)
    if kid_id is None:
        return None
    security_crud.mark_login_token_used(db, login_row_id)
    return _attach_info(db, kids_crud.get_kid_by_id_only(db, kid_id))


# ---------- QR login: confirm ----------
# no token here — resolve already killed it. this step is plain
# kid_id + password, issuing the session on success.

def confirm_login(db: Session, kid_id: int, password: str, remember_me: bool, device_info: str | None):
    if not security_crud.verify_kid_password(db, kid_id, password):
        return None, None, None

    kid = _attach_info(db, kids_crud.get_kid_by_id_only(db, kid_id))
    token, record = session_crud.issue_session(db, "kid", kid_id, remember_me, device_info)
    return kid, token, record

# ---------- dashboard ----------
# kid app never calls kidsmanager's /kids/me directly — this is the
# facade route. Currently just re-exposes the kid's own profile; room
# to aggregate more (assignments, school data) once schoolmanager exists.

def get_dashboard(db: Session, kid_id: int):
    kid = kids_crud.get_kid_by_id_only(db, kid_id)
    if not kid:
        return None
    info = kids_crud.get_kid_info(db, kid_id)
    activated = school_crud.is_school_activated(db, kid_id)
    setup_complete = school_crud.has_matched_subject(db, kid_id)
    subjects = school_crud.get_subjects(db, kid_id)
    teachers = school_crud.get_teachers(db, kid_id)
    return kid, info, activated, setup_complete, subjects, teachers


def assign_subject_teacher(db: Session, kid_id: int, subject_id: int, teacher_id: int):
    return school_crud.assign_subject_teacher(db, kid_id, subject_id, teacher_id)



# ---------- reset password (kid side) ----------

def verify_reset_code(db: Session, kid_id: int, code: str) -> bool:
    return security_crud.verify_kid_reset_code_by_kid(db, kid_id, code)


def set_new_password(db: Session, kid_id: int, new_password: str) -> bool:
    return security_crud.consume_kid_reset_code_by_kid(db, kid_id, new_password)


# ---------- game: wallet ----------
# thin passthrough - facade exists so kid app never calls gamemanager
# directly, same rule as dashboard above.

def get_wallet(db: Session, kid_id: int):
    return game_crud.get_or_create_wallet(db, kid_id)


# ---------- game: crossword next levels ----------

def get_next_crossword_levels(db: Session, kid_id: int, batch_size: int = 5):
    return game_crud.get_next_levels(db, kid_id, "crossword", batch_size)


# ---------- game: bundled home payload ----------

def get_game_home(db: Session, kid_id: int):
    wallet = get_wallet(db, kid_id)
    current_level, levels = get_next_crossword_levels(db, kid_id)
    progress = game_crud.get_or_create_progress(db, kid_id, "crossword")
    streak_active = game_crud.is_streak_active(progress)
    return wallet, current_level, levels, progress, streak_active


# ---------- game: slot solved ----------

def report_slot_solved(db, kid_id: int, level_id: int, slot_number: int):
    level = game_crud.get_level_by_id(db, level_id)
    if not level:
        return None

    xp_awarded = 0
    if game_crud.mark_slot_solved(db, kid_id, level.id, slot_number):
        game_crud.add_xp(db, kid_id, game_crud.XP_SLOT_SOLVED)
        xp_awarded = game_crud.XP_SLOT_SOLVED

    slot = next((s for s in level.slots if s["number"] == slot_number), None)
    if not slot or not slot.get("bonus_coins") or game_crud.has_claimed_bonus(db, kid_id, level.id, slot_number):
        wallet = game_crud.get_or_create_wallet(db, kid_id)
        return False, 0, wallet, xp_awarded
    wallet = game_crud.claim_bonus(db, kid_id, level.id, slot_number, slot["bonus_coins"])
    return True, slot["bonus_coins"], wallet, xp_awarded


# ---------- game: level complete ----------

def report_level_complete(db, kid_id: int, level_id: int):
    level = game_crud.get_level_by_id(db, level_id)
    if not level:
        return None
    wallet, progress, xp_awarded = game_crud.complete_level(db, kid_id, level)
    return level, wallet, progress, xp_awarded


# ---------- game: leaderboard ----------

def get_leaderboard(db, limit: int = 50):
    return game_crud.get_leaderboard(db, limit=limit)

from schoolmanager import crud as school_crud, logic as school_logic


def list_subjects(db, kid_id):
    return school_crud.get_subjects(db, kid_id)


def update_subject(db, kid_id, subject_id, name):
    return school_crud.update_subject(db, kid_id, subject_id, name)


def list_teachers(db, kid_id):
    return school_crud.get_teachers(db, kid_id)


def set_favorite_subject(db, kid_id, subject_id):
    return school_crud.set_favorite_subject(db, kid_id, subject_id)


def update_teacher(db, kid_id, teacher_id, name, phone, email):
    if phone and not school_logic.is_valid_phone(phone):
        raise ValueError("Invalid phone")
    if email and not school_logic.is_valid_email(email):
        raise ValueError("Invalid email")
    return school_crud.update_teacher(db, kid_id, teacher_id, name, phone, email)
