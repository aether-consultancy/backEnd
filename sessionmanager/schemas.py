from pydantic import BaseModel


class SessionOut(BaseModel):
    token: str
    expires_at: str


class SessionValidateOut(BaseModel):
    owner_type: str
    owner_id: int
