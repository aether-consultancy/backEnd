from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from dbmanager.connection import Base


class Kid(Base):
    __tablename__ = "kids"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False)
    school = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    learning_system = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KidInfo(Base):
    __tablename__ = "kid_info"

    kid_id = Column(Integer, ForeignKey("kids.id"), primary_key=True, index=True)
    nickname = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    favorite_color = Column(String, nullable=True)
    favorite_animal = Column(String, nullable=True)
    subjects_loved = Column(JSON, nullable=True)
