from sqlalchemy.orm import Session
from . import models, logic

def create_subject(db: Session, kid_id: int, name: str):
    code = logic.generate_subject_code(name)
    while db.query(models.Subject).filter(models.Subject.code == code).first():
        code = logic.generate_subject_code(name)
    subject = models.Subject(kid_id=kid_id, name=name.strip(), code=code)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

def get_subjects(db: Session, kid_id: int):
    return db.query(models.Subject).filter(models.Subject.kid_id == kid_id).all()

def get_subject(db: Session, kid_id: int, subject_id: int):
    return db.query(models.Subject).filter(
        models.Subject.id == subject_id, models.Subject.kid_id == kid_id
    ).first()

def update_subject(db: Session, kid_id: int, subject_id: int, name: str):
    subject = get_subject(db, kid_id, subject_id)
    if not subject:
        return None
    subject.name = name.strip()
    db.commit()
    db.refresh(subject)
    return subject

def delete_subject(db: Session, kid_id: int, subject_id: int):
    subject = get_subject(db, kid_id, subject_id)
    if not subject:
        return False
    db.delete(subject)
    db.commit()
    return True

def create_teacher(db: Session, kid_id: int, name: str, phone: str, email: str = None):
    teacher = models.Teacher(
        kid_id=kid_id, name=name.strip(),
        phone=logic.normalize_phone(phone), email=email
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher

def get_teachers(db: Session, kid_id: int):
    return db.query(models.Teacher).filter(models.Teacher.kid_id == kid_id).all()

def get_teacher(db: Session, kid_id: int, teacher_id: int):
    return db.query(models.Teacher).filter(
        models.Teacher.id == teacher_id, models.Teacher.kid_id == kid_id
    ).first()

def update_teacher(db: Session, kid_id: int, teacher_id: int, name: str = None, phone: str = None, email: str = None):
    teacher = get_teacher(db, kid_id, teacher_id)
    if not teacher:
        return None
    if name is not None:
        teacher.name = name.strip()
    if phone is not None:
        teacher.phone = logic.normalize_phone(phone)
    if email is not None:
        teacher.email = email
    db.commit()
    db.refresh(teacher)
    return teacher

def delete_teacher(db: Session, kid_id: int, teacher_id: int):
    teacher = get_teacher(db, kid_id, teacher_id)
    if not teacher:
        return False
    db.delete(teacher)
    db.commit()
    return True
