from pydantic import BaseModel, EmailStr


class ParentSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str | None = None
    terms_accepted: bool
    preferred_language: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    relation: str | None = None
    family_name_for_kids: str | None = None


class ParentLogin(BaseModel):
    email: EmailStr
    password: str


class ParentOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    preferred_language: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    relation: str | None = None
    family_name_for_kids: str | None = None

    class Config:
        from_attributes = True
