from sqlalchemy import Column, String, Integer, ForeignKey, JSON, DateTime, Boolean, func
from sqlalchemy.orm import relationship, backref
from app.db.connection import Base


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    relation = Column(String, nullable=True)  # mother/father/sister/brother/guardian
    nickname = Column(String, nullable=True)
    home_address = Column(String, nullable=True)
    preferred_language = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    info_completed = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    kids = relationship("Kid", back_populates="parent")


class Kid(Base):
    __tablename__ = "kids"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False)
    full_name = Column(String, nullable=False)
    school = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    learning_system = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # set by kid during QR-scan flow
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("Parent", back_populates="kids")


class KidInfo(Base):
    __tablename__ = "kid_info"

    kid_id = Column(Integer, ForeignKey("kids.id"), primary_key=True, index=True)
    nickname = Column(String, nullable=True)
    subjects_loved = Column(JSON, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    age = Column(Integer, nullable=True)
    favorite_color = Column(String, nullable=True)
    favorite_animal = Column(String, nullable=True)

    kid = relationship("Kid", backref=backref("info", uselist=False))


class KidClaimToken(Base):
    __tablename__ = "kid_claim_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    kid = relationship("Kid")


class UserProgress(Base):
    __tablename__ = "user_progress"

    kid_id = Column(Integer, ForeignKey("kids.id"), primary_key=True, index=True)
    data = Column(JSON, nullable=False, default=dict)
