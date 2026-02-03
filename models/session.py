from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class TokenType(str, enum.Enum):
    session = "session"
    refresh = "refresh"
    password_reset = "password_reset"


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=False)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())
    login_at = Column(DateTime, server_default=func.now())
    logout_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    refresh_token_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")


class BlockedToken(Base):
    __tablename__ = "blocked_tokens"

    blocked_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.session_id", ondelete="SET NULL"), nullable=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    token_type = Column(Enum(TokenType), default=TokenType.session)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_reason = Column(String(255), nullable=True)
    blocked_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())