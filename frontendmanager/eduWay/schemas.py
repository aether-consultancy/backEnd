from pydantic import BaseModel
from kidsmanager.schemas import KidOut, KidProfileOut
from gamemanager.schemas import WalletOut, GameLevelOut


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


# ---------- reset password (kid verifies code + sets new password) ----------

class ResetPasswordVerifyIn(BaseModel):
    kid_id: int
    code: str

class ResetPasswordVerifyOut(BaseModel):
    proof_token: str

class ResetPasswordSetIn(BaseModel):
    proof_token: str
    new_password: str

class ResetPasswordSetOut(BaseModel):
    status: str


# ---------- game: bundled home payload ----------
# one call for the world/trail screen - wallet + next crossword levels
# together, so the FE doesn't fire two requests on mount.

class GameHomeOut(BaseModel):
    wallet: WalletOut
    current_level: int
    levels: list[GameLevelOut]
    current_streak: int
    longest_streak: int
    streak_active: bool
