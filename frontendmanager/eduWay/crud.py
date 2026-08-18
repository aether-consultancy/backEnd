from sqlalchemy.orm import Session

from kidsmanager.models import Kid
from kidsmanager import crud as kids_crud
from securitymanager import crud as security_crud
from sessionmanager import crud as session_crud


# ---------- claim preview ----------
# read-only: validates the claim token without consuming it, fetches
# the kid record the parent already created so the kid app can show
# "is this you" before any password is set.

def preview_claim(db: Session, claim_row_id: int, token: str) -> Kid | None:
    kid_id = security_crud.resolve_claim_token(db, token, claim_row_id)
    if kid_id is None:
        return None
    return kids_crud.get_kid_by_id_only(db, kid_id)


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
    return kids_crud.get_kid_by_id_only(db, kid_id)


# ---------- QR login: confirm ----------
# no token here — resolve already killed it. this step is plain
# kid_id + password, issuing the session on success.

def confirm_login(db: Session, kid_id: int, password: str, remember_me: bool, device_info: str | None):
    if not security_crud.verify_kid_password(db, kid_id, password):
        return None, None, None

    kid = kids_crud.get_kid_by_id_only(db, kid_id)
    token, record = session_crud.issue_session(db, "kid", kid_id, remember_me, device_info)
    return kid, token, record
