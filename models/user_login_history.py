from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class LoginStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    locked = "locked"


class UserLoginHistory(Base):
    __tablename__ = "user_login_history"

    login_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    login_timestamp = Column(DateTime, server_default=func.now(), index=True)
    ip_address = Column(String(45), nullable=True)
    device_type = Column(String(50), nullable=True)
    device_name = Column(String(255), nullable=True)
    browser_info = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    login_status = Column(Enum(LoginStatus), default=LoginStatus.success)
    failure_reason = Column(String(255), nullable=True)
    session_id = Column(Integer, ForeignKey("user_sessions.session_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="login_history")