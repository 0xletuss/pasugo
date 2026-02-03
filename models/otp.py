from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class OTPType(str, enum.Enum):
    registration = "registration"
    login = "login"
    password_reset = "password_reset"
    phone_verification = "phone_verification"


class OTP(Base):
    __tablename__ = "otps"

    otp_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    otp_code = Column(String(10), nullable=False, index=True)
    otp_type = Column(Enum(OTPType), nullable=False)
    phone_number = Column(String(20), nullable=False)
    is_verified = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="otps")