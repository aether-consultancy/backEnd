import re, random, string
from sqlalchemy.orm import Session
from . import models

PHONE_REGEX = re.compile(r"^\+[1-9][0-9]{7,14}$")

def normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-]", "", phone)

def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_REGEX.match(phone))

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def generate_subject_code(name: str) -> str:
    initials = "".join(w[0] for w in name.strip().split()).upper()
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{initials}{suffix}"

def subject_exists(db: Session, kid_id: int, name: str) -> bool:
    return db.query(models.Subject).filter(
        models.Subject.kid_id == kid_id,
        models.Subject.name.ilike(name.strip())
    ).first() is not None

def teacher_exists(db: Session, kid_id: int, name: str, phone: str) -> bool:
    return db.query(models.Teacher).filter(
        models.Teacher.kid_id == kid_id,
        models.Teacher.name.ilike(name.strip()),
        models.Teacher.phone == normalize_phone(phone)
    ).first() is not None
