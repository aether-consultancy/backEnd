from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from dbmanager.connection import Base


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
