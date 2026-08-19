from pydantic import BaseModel
from kidsmanager.schemas import KidOut, KidProfileOut


class ClaimPreviewOut(BaseModel):
    kid: KidOut
    is_claimed: bool


class ClaimConfirmIn(BaseModel):
    password: str


class ClaimConfirmOut(BaseModel):
    kid_id: int
    proof_token: str


class MoreInfoIn(BaseModel):
    proof_token: str
    nickname: str | None = None
    age: int | None = None
    favorite_color: str | None = None
    favorite_animal: str | None = None
    subjects_loved: list[str] | None = None
    remember_me: bool = False
    device_info: str | None = None


class MoreInfoOut(BaseModel):
    kid: KidProfileOut
    token: str
    expires_at: str


class LoginResolveOut(BaseModel):
    kid: KidOut


class LoginConfirmIn(BaseModel):
    kid_id: int
    password: str
    remember_me: bool = False
    device_info: str | None = None


class LoginConfirmOut(BaseModel):
    kid: KidOut
    token: str
    expires_at: str


class LogoutOut(BaseModel):
    status: str
