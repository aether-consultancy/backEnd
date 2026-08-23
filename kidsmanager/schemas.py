from pydantic import BaseModel


class KidCreate(BaseModel):
    full_name: str
    school: str
    grade: str
    learning_system: str


class KidOut(BaseModel):
    id: int
    full_name: str
    school: str
    grade: str
    learning_system: str
    nickname: str | None = None
    favorite_animal: str | None = None

    class Config:
        from_attributes = True


class KidInfoUpdate(BaseModel):
    nickname: str | None = None
    age: int | None = None
    favorite_color: str | None = None
    favorite_animal: str | None = None
    subjects_loved: list[str] | None = None


class KidProfileOut(BaseModel):
    id: int
    full_name: str
    school: str
    grade: str
    learning_system: str
    nickname: str | None = None
    age: int | None = None
    favorite_color: str | None = None
    favorite_animal: str | None = None
    subjects_loved: list[str] | None = None


class KidEdit(BaseModel):
    full_name: str | None = None
    school: str | None = None
    grade: str | None = None
    learning_system: str | None = None
