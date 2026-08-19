from sqlalchemy import Column, Integer, String, DateTime, Boolean, CheckConstraint, func
from dbmanager.connection import Base


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True, unique=True)

    terms_accepted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    onboarding_completed = Column(Boolean, nullable=False, default=False, server_default="false")

    preferred_language = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    relation = Column(String, nullable=True)
    family_name_for_kids = Column(String, nullable=True)

    parent_since = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("phone ~ '^\\+[1-9][0-9]{7,14}$'", name="phone_must_have_country_code"),
    )
