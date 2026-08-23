from pydantic import BaseModel
from parentmanager.schemas import ParentOut


class SignupOut(BaseModel):
    parent: ParentOut
    verification_id: int
    verification_expires_at: str


class MoreInfoIn(BaseModel):
    proof_token: str
    full_name: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    relation: str | None = None
    family_name_for_kids: str | None = None
    remember_me: bool = False
    device_info: str | None = None


class MoreInfoOut(BaseModel):
    parent: ParentOut
    token: str
    expires_at: str


class LoginIn(BaseModel):
    email: str
    password: str
    remember_me: bool = False
    device_info: str | None = None


class LoginOut(BaseModel):
    parent: ParentOut
    token: str
    expires_at: str


class LogoutAllOut(BaseModel):
    sessions_revoked: int

from kidsmanager.schemas import KidProfileOut, KidOut


class KidProfileWithStatusOut(KidProfileOut):
    claimed: bool
    current_streak: int
    longest_streak: int
    streak_active: bool

class DashboardOut(BaseModel):
    parent: ParentOut
    kids: list[KidOut]



# ---------- reset kid password (parent generates code) ----------

class ResetKidPasswordOut(BaseModel):
    code: str
    expires_at: str
