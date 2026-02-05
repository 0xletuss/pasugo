from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum, Float, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class RiderStatus(str, enum.Enum):
    available = "available"
    busy = "busy"
    offline = "offline"
    suspended = "suspended"


class Rider(Base):
    __tablename__ = "riders"

    rider_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    id_number = Column(String(50), nullable=False, unique=True)
    id_document_url = Column(String(500), nullable=True)  # Cloudinary URL for ID document
    vehicle_type = Column(String(50), nullable=True)
    vehicle_plate = Column(String(50), nullable=True)
    license_number = Column(String(50), nullable=True)  # Driver's license number
    availability_status = Column(Enum(RiderStatus), default=RiderStatus.offline, index=True)
    rating = Column(DECIMAL(3, 2), default=0.00, index=True)
    total_tasks_completed = Column(Integer, default=0)
    total_earnings = Column(DECIMAL(10, 2), default=0.00)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="rider_profile")
    bill_requests = relationship("BillRequest", back_populates="rider")
    ratings = relationship("Rating", back_populates="rider")
    payments = relationship("Payment", back_populates="rider")
    tasks = relationship("RiderTask", back_populates="rider")