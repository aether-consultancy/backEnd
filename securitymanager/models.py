from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from dbmanager.connection import Base


class ParentPassword(Base):
    __tablename__ = "parent_passwords"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KidPassword(Base):
    __tablename__ = "kid_passwords"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KidClaimToken(Base):
    __tablename__ = "kid_claim_tokens"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from dbmanager.connection import Base


class KidLoginToken(Base):
    __tablename__ = "kid_login_tokens"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from dbmanager.connection import Base


class ParentResetCode(Base):
    __tablename__ = "parent_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KidResetCode(Base):
    __tablename__ = "kid_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
