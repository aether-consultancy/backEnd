from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SubjectCreate(BaseModel):
    name: str

class SubjectUpdate(BaseModel):
    name: Optional[str] = None

class SubjectOut(BaseModel):
    id: int
    kid_id: int
    name: str
    code: str
    teacher_id: Optional[int] = None
    is_favorite: bool = False
    created_at: datetime
    class Config:
        from_attributes = True

class TeacherCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None

class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class TeacherOut(BaseModel):
    id: int
    kid_id: int
    name: str
    phone: str
    email: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class SubjectTeacherAssignIn(BaseModel):
    teacher_id: int
