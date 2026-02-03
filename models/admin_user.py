from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    manager = "manager"
    support = "support"


class AdminUser(Base):
    __tablename__ = "admin_users"

    admin_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    role = Column(Enum(AdminRole), default=AdminRole.support, index=True)
    permissions = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="admin_profile")