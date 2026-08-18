from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from dbmanager.connection import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_type = Column(String, nullable=False, index=True)
    owner_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    remember_me = Column(Boolean, nullable=False, default=False)
    device_info = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
