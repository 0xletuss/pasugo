from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class AppTheme(str, enum.Enum):
    light = "light"
    dark = "dark"


class UserPreference(Base):
    __tablename__ = "user_preferences"

    preference_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    remember_me = Column(Boolean, default=True)
    auto_login = Column(Boolean, default=True)
    notification_enabled = Column(Boolean, default=True)
    push_notification_enabled = Column(Boolean, default=True)
    email_notification_enabled = Column(Boolean, default=True)
    sms_notification_enabled = Column(Boolean, default=False)
    app_theme = Column(Enum(AppTheme), default=AppTheme.light)
    language = Column(String(10), default="en")
    currency = Column(String(10), default="PHP")
    biometric_auth_enabled = Column(Boolean, default=False)
    face_recognition_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")