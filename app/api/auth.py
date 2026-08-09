from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import jwt
import secrets
from datetime import datetime, timedelta, timezone

from app.db.connection import get_db
from app.db.models import Parent, Kid, KidInfo, KidClaimToken, UserProgress
from app.security.hashing import hash_password, verify_password
from app.security.tokens import create_access_token, decode_token, token_ttl_seconds
from app.api.deps import get_current_parent, get_current_kid
from app.cache.redis_client import redis_client
import json

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["auth"])


class ParentSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class ParentLogin(BaseModel):
    email: EmailStr
    password: str


class ParentOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    gender: str | None = None
    relation: str | None = None
    nickname: str | None = None
    home_address: str | None = None
    preferred_language: str | None = None
    avatar_url: str | None = None
    info_completed: bool

    class Config:
        from_attributes = True


class ParentMoreInfo(BaseModel):
    gender: str
    nickname: str
    phone: str | None = None
    home_address: str | None = None
    preferred_language: str | None = None
    avatar_url: str | None = None


class KidCreate(BaseModel):
    full_name: str
    school: str
    grade: str
    learning_system: str


class ClaimTokenOut(BaseModel):
    token: str
    expires_at: str


class ClaimPreviewOut(BaseModel):
    kid_id: int
    full_name: str
    school: str | None = None
    grade: str | None = None
    is_claimed: bool = False


class ClaimConfirm(BaseModel):
    password: str


class KidSetPassword(BaseModel):
    kid_id: int
    password: str


class KidLogin(BaseModel):
    kid_id: int
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/parent/signup", response_model=TokenOut)
def parent_signup(payload: ParentSignup, db: Session = Depends(get_db)):
    if db.query(Parent).filter(Parent.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    parent = Parent(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)

    token = create_access_token({"sub": str(parent.id), "type": "parent"})
    return TokenOut(access_token=token)


@router.post("/parent/login", response_model=TokenOut)
def parent_login(payload: ParentLogin, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.email == payload.email).first()
    if not parent or not verify_password(payload.password, parent.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = create_access_token({"sub": str(parent.id), "type": "parent"})
    return TokenOut(access_token=token)


def _parent_cache_key(parent_id: int) -> str:
    return f"parent:{parent_id}"


def _serialize_parent(parent: Parent) -> dict:
    return {
        "id": parent.id,
        "full_name": parent.full_name,
        "email": parent.email,
        "phone": parent.phone,
        "gender": parent.gender,
        "relation": parent.relation,
        "nickname": parent.nickname,
        "home_address": parent.home_address,
        "preferred_language": parent.preferred_language,
        "avatar_url": parent.avatar_url,
        "info_completed": parent.info_completed,
    }


def _cache_parent(parent: Parent):
    redis_client.setex(_parent_cache_key(parent.id), 3600, json.dumps(_serialize_parent(parent)))


def _invalidate_parent_cache(parent_id: int):
    redis_client.delete(_parent_cache_key(parent_id))


@router.get("/parent/me", response_model=ParentOut)
def parent_me(parent: Parent = Depends(get_current_parent)):
    cached = redis_client.get(_parent_cache_key(parent.id))
    if cached:
        return json.loads(cached)
    _cache_parent(parent)
    return _serialize_parent(parent)


@router.patch("/parent/more-info", response_model=ParentOut)
def parent_more_info(
    payload: ParentMoreInfo,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    parent.gender = payload.gender
    parent.nickname = payload.nickname
    if payload.phone is not None:
        parent.phone = payload.phone
    parent.home_address = payload.home_address
    parent.preferred_language = payload.preferred_language
    parent.avatar_url = payload.avatar_url
    parent.info_completed = True
    db.commit()
    db.refresh(parent)
    _cache_parent(parent)
    return parent


class ParentAccountUpdate(BaseModel):
    full_name: str | None = None
    nickname: str | None = None
    gender: str | None = None
    relation: str | None = None
    phone: str | None = None
    home_address: str | None = None
    preferred_language: str | None = None


@router.patch("/parent/account-details", response_model=ParentOut)
def update_account_details(
    payload: ParentAccountUpdate,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(parent, field, value)
    db.commit()
    db.refresh(parent)
    _cache_parent(parent)
    return parent


@router.get("/kids/{kid_id}")
def get_kid(
    kid_id: int,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    kid = db.query(Kid).filter(Kid.id == kid_id, Kid.parent_id == parent.id).first()
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")

    info = db.query(KidInfo).filter(KidInfo.kid_id == kid.id).first()
    progress = db.query(UserProgress).filter(UserProgress.kid_id == kid.id).first()
    progress_data = (progress.data if progress else {}) or {}

    return {
        "id": kid.id,
        "full_name": kid.full_name,
        "school": kid.school,
        "grade": kid.grade,
        "learning_system": kid.learning_system,
        "nickname": info.nickname if info else None,
        "subjects_loved": info.subjects_loved if info else None,
        "confirmed_at": info.confirmed_at.isoformat() if info and info.confirmed_at else None,
        "age": info.age if info else None,
        "favorite_color": info.favorite_color if info else None,
        "favorite_animal": info.favorite_animal if info else None,
        "metrics": {
            "streak_days": progress_data.get("streak_days", 0),
            "minutes_learned": progress_data.get("minutes_learned", 0),
            "badges_earned": progress_data.get("badges_earned", 0),
        },
    }


@router.get("/kids")
def list_kids(
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    kids = db.query(Kid).filter(Kid.parent_id == parent.id).order_by(Kid.created_at.asc()).all()
    return [
        {
            "id": kid.id,
            "full_name": kid.full_name,
            "school": kid.school,
            "grade": kid.grade,
            "learning_system": kid.learning_system,
            "favorite_animal": kid.info.favorite_animal if kid.info else None,
            "favorite_color": kid.info.favorite_color if kid.info else None,
        }
        for kid in kids
    ]


@router.post("/kids", status_code=status.HTTP_201_CREATED)
def create_kid(
    payload: KidCreate,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    existing = (
        db.query(Kid)
        .filter(Kid.parent_id == parent.id, Kid.full_name.ilike(payload.full_name.strip()))
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A scholar with this name already exists on your account")

    kid = Kid(
        parent_id=parent.id,
        full_name=payload.full_name,
        school=payload.school,
        grade=payload.grade,
        learning_system=payload.learning_system,
    )
    db.add(kid)
    db.commit()
    db.refresh(kid)
    return {"kid_id": kid.id, "full_name": kid.full_name}


CLAIM_TOKEN_TTL_HOURS = 24


@router.post("/kids/{kid_id}/claim-token", response_model=ClaimTokenOut)
def create_claim_token(
    kid_id: int,
    db: Session = Depends(get_db),
    parent: Parent = Depends(get_current_parent),
):
    kid = db.query(Kid).filter(Kid.id == kid_id, Kid.parent_id == parent.id).first()
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")

    db.query(KidClaimToken).filter(
        KidClaimToken.kid_id == kid.id,
        KidClaimToken.used_at.is_(None),
    ).delete()

    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=CLAIM_TOKEN_TTL_HOURS)

    claim = KidClaimToken(token=token, kid_id=kid.id, expires_at=expires_at)
    db.add(claim)
    db.commit()

    return ClaimTokenOut(token=token, expires_at=expires_at.isoformat())


@router.get("/kids/claim/{token}", response_model=ClaimPreviewOut)
def preview_claim(token: str, db: Session = Depends(get_db)):
    claim = db.query(KidClaimToken).filter(KidClaimToken.token == token).first()
    if not claim or claim.used_at is not None or claim.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")

    kid = db.query(Kid).filter(Kid.id == claim.kid_id).first()
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")

    return ClaimPreviewOut(
        kid_id=kid.id,
        full_name=kid.full_name,
        school=kid.school,
        grade=kid.grade,
        is_claimed=bool(kid.password_hash),
    )


@router.post("/kids/claim/{token}/confirm", response_model=TokenOut)
def confirm_claim(token: str, payload: ClaimConfirm, db: Session = Depends(get_db)):
    claim = db.query(KidClaimToken).filter(KidClaimToken.token == token).first()
    if not claim or claim.used_at is not None or claim.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired code")

    kid = db.query(Kid).filter(Kid.id == claim.kid_id).first()
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    if kid.password_hash:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kid already claimed")

    kid.password_hash = hash_password(payload.password)

    info = db.query(KidInfo).filter(KidInfo.kid_id == kid.id).first()
    if not info:
        info = KidInfo(kid_id=kid.id)
        db.add(info)
    info.confirmed_at = datetime.now(timezone.utc)

    claim.used_at = datetime.now(timezone.utc)

    db.commit()

    access_token = create_access_token({"sub": str(kid.id), "type": "kid"})
    return TokenOut(access_token=access_token)


@router.post("/kids/set-password", response_model=TokenOut)
def kid_set_password(payload: KidSetPassword, db: Session = Depends(get_db)):
    kid = db.query(Kid).filter(Kid.id == payload.kid_id).first()
    if not kid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kid not found")
    if kid.password_hash:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password already set")

    kid.password_hash = hash_password(payload.password)
    db.commit()

    token = create_access_token({"sub": str(kid.id), "type": "kid"})
    return TokenOut(access_token=token)


@router.post("/kids/login", response_model=TokenOut)
def kid_login(payload: KidLogin, db: Session = Depends(get_db)):
    kid = db.query(Kid).filter(Kid.id == payload.kid_id).first()
    if not kid or not kid.password_hash or not verify_password(payload.password, kid.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = create_access_token({"sub": str(kid.id), "type": "kid"})
    return TokenOut(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        claims = decode_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    ttl = token_ttl_seconds(claims)
    if ttl > 0:
        redis_client.setex(f"blacklist:{token}", ttl, "1")


class KidMoreInfo(BaseModel):
    nickname: str | None = None
    age: int | None = None
    favorite_color: str | None = None
    favorite_animal: str | None = None
    subjects_loved: list[str] | None = None


@router.get("/me")
def get_my_kid_profile(
    db: Session = Depends(get_db),
    kid: Kid = Depends(get_current_kid),
):
    info = db.query(KidInfo).filter(KidInfo.kid_id == kid.id).first()
    return {
        "id": kid.id,
        "full_name": kid.full_name,
        "school": kid.school,
        "school_name": kid.school,
        "grade": kid.grade,
        "learning_system": kid.learning_system,
        "nickname": info.nickname if info else None,
        "age": info.age if info else None,
        "favorite_color": info.favorite_color if info else None,
        "favorite_animal": info.favorite_animal if info else None,
        "subjects_loved": info.subjects_loved if info else None,
    }


@router.patch("/me")
def update_my_kid_profile(
    payload: KidMoreInfo,
    db: Session = Depends(get_db),
    kid: Kid = Depends(get_current_kid),
):
    info = db.query(KidInfo).filter(KidInfo.kid_id == kid.id).first()
    if not info:
        info = KidInfo(kid_id=kid.id)
        db.add(info)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(info, field, value)

    db.commit()
    db.refresh(info)

    return {
        "id": kid.id,
        "full_name": kid.full_name,
        "school": kid.school,
        "grade": kid.grade,
        "learning_system": kid.learning_system,
        "nickname": info.nickname,
        "age": info.age,
        "favorite_color": info.favorite_color,
        "favorite_animal": info.favorite_animal,
        "subjects_loved": info.subjects_loved,
    }
