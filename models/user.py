from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserType(str, enum.Enum):
    customer = "customer"
    rider = "rider"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False, index=True)
    address = Column(Text, nullable=True)
    profile_photo_url = Column(String(500), nullable=True)  # Cloudinary URL for profile photo
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    bill_requests = relationship("BillRequest", back_populates="customer", foreign_keys="BillRequest.customer_id")
    complaints = relationship("Complaint", back_populates="customer")
    sessions = relationship("UserSession", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    otps = relationship("OTP", back_populates="user")
    login_history = relationship("UserLoginHistory", back_populates="user")
    devices = relationship("UserDevice", back_populates="user")
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    admin_profile = relationship("AdminUser", back_populates="user", uselist=False)
    rider_profile = relationship("Rider", back_populates="user", uselist=False)
    payments = relationship("Payment", back_populates="customer")
    ratings_given = relationship("Rating", back_populates="customer")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")