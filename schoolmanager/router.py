from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dbmanager.connection import get_db
from sessionmanager.deps import get_current_parent, get_current_kid
from . import crud, schemas, logic

router = APIRouter(prefix="/school", tags=["school"])

# ---- parent: full CRUD, scoped by kid_id in path ----

# STALE @router.post("/parent/{kid_id}/subjects", response_model=schemas.SubjectOut)
# STALE def create_subject(kid_id: int, body: schemas.SubjectCreate, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     if logic.subject_exists(db, kid_id, body.name):
# STALE         raise HTTPException(400, "Subject already exists")
# STALE     return crud.create_subject(db, kid_id, body.name)

# STALE @router.get("/parent/{kid_id}/subjects", response_model=list[schemas.SubjectOut])
# STALE def list_subjects_parent(kid_id: int, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     return crud.get_subjects(db, kid_id)

# STALE @router.patch("/parent/{kid_id}/subjects/{subject_id}", response_model=schemas.SubjectOut)
# STALE def update_subject_parent(kid_id: int, subject_id: int, body: schemas.SubjectUpdate, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     subject = crud.update_subject(db, kid_id, subject_id, body.name)
# STALE     if not subject:
# STALE         raise HTTPException(404, "Subject not found")
# STALE     return subject

# STALE @router.delete("/parent/{kid_id}/subjects/{subject_id}")
# STALE def delete_subject_parent(kid_id: int, subject_id: int, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     if not crud.delete_subject(db, kid_id, subject_id):
# STALE         raise HTTPException(404, "Subject not found")
# STALE     return {"deleted": True}

# STALE @router.post("/parent/{kid_id}/teachers", response_model=schemas.TeacherOut)
# STALE def create_teacher(kid_id: int, body: schemas.TeacherCreate, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     if not logic.is_valid_phone(body.phone):
# STALE         raise HTTPException(400, "Invalid phone")
# STALE     if body.email and not logic.is_valid_email(body.email):
# STALE         raise HTTPException(400, "Invalid email")
# STALE     if logic.teacher_exists(db, kid_id, body.name, body.phone):
# STALE         raise HTTPException(400, "Teacher already exists")
# STALE     return crud.create_teacher(db, kid_id, body.name, body.phone, body.email)

# STALE @router.get("/parent/{kid_id}/teachers", response_model=list[schemas.TeacherOut])
# STALE def list_teachers_parent(kid_id: int, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     return crud.get_teachers(db, kid_id)

# STALE @router.patch("/parent/{kid_id}/teachers/{teacher_id}", response_model=schemas.TeacherOut)
# STALE def update_teacher_parent(kid_id: int, teacher_id: int, body: schemas.TeacherUpdate, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     if body.phone and not logic.is_valid_phone(body.phone):
# STALE         raise HTTPException(400, "Invalid phone")
# STALE     if body.email and not logic.is_valid_email(body.email):
# STALE         raise HTTPException(400, "Invalid email")
# STALE     teacher = crud.update_teacher(db, kid_id, teacher_id, body.name, body.phone, body.email)
# STALE     if not teacher:
# STALE         raise HTTPException(404, "Teacher not found")
# STALE     return teacher

# STALE @router.delete("/parent/{kid_id}/teachers/{teacher_id}")
# STALE def delete_teacher_parent(kid_id: int, teacher_id: int, db: Session = Depends(get_db), parent=Depends(get_current_parent)):
# STALE     if not crud.delete_teacher(db, kid_id, teacher_id):
# STALE         raise HTTPException(404, "Teacher not found")
# STALE     return {"deleted": True}

# ---- kid: get + edit only, scoped to own session, no kid_id in path ----

# STALE @router.get("/kid/subjects", response_model=list[schemas.SubjectOut])
# STALE def list_subjects_kid(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
# STALE     return crud.get_subjects(db, kid.id)

# STALE @router.patch("/kid/subjects/{subject_id}", response_model=schemas.SubjectOut)
# STALE def update_subject_kid(subject_id: int, body: schemas.SubjectUpdate, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
# STALE     subject = crud.update_subject(db, kid.id, subject_id, body.name)
# STALE     if not subject:
# STALE         raise HTTPException(404, "Subject not found")
# STALE     return subject

# STALE @router.get("/kid/teachers", response_model=list[schemas.TeacherOut])
# STALE def list_teachers_kid(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
# STALE     return crud.get_teachers(db, kid.id)

# STALE @router.patch("/kid/teachers/{teacher_id}", response_model=schemas.TeacherOut)
# STALE def update_teacher_kid(teacher_id: int, body: schemas.TeacherUpdate, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
# STALE     if body.phone and not logic.is_valid_phone(body.phone):
# STALE         raise HTTPException(400, "Invalid phone")
# STALE     if body.email and not logic.is_valid_email(body.email):
# STALE         raise HTTPException(400, "Invalid email")
# STALE     teacher = crud.update_teacher(db, kid.id, teacher_id, body.name, body.phone, body.email)
# STALE     if not teacher:
# STALE         raise HTTPException(404, "Teacher not found")
# STALE     return teacher
