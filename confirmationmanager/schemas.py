from pydantic import BaseModel


class VerificationCodeOut(BaseModel):
    verification_id: int
    expires_at: str


class VerificationCodeVerify(BaseModel):
    code: str


class VerificationStatusOut(BaseModel):
    parent_id: int
    verified: bool
