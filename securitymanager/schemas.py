from pydantic import BaseModel


class KidTokenOut(BaseModel):
    token: str
    expires_at: str


class ClaimConfirm(BaseModel):
    password: str


class KidLoginConfirm(BaseModel):
    password: str


class ResetCodeOut(BaseModel):
    reset_id: int
    expires_at: str


class ResetCodeVerify(BaseModel):
    code: str


class ResetPasswordSet(BaseModel):
    new_password: str
