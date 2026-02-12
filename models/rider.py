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
    id_document_url = Column(String(500), nullable=True)
    vehicle_type = Column(String(50), nullable=True)
    vehicle_plate = Column(String(50), nullable=True)
    license_number = Column(String(50), nullable=True)
    availability_status = Column(Enum(RiderStatus), default=RiderStatus.offline, index=True)
    rating = Column(DECIMAL(3, 2), default=0.00, index=True)
    total_tasks_completed = Column(Integer, default=0)
    total_earnings = Column(DECIMAL(10, 2), default=0.00)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="rider_profile")
    bill_requests = relationship("BillRequest", back_populates="rider")

    # Assigned requests (rider_id FK) - the rider who is doing the job
    requests = relationship(
        "Request",
        foreign_keys="[Request.rider_id]",
        back_populates="rider"
    )

    # Requests where this rider has been selected/notified (selected_rider_id FK)
    selected_requests = relationship(
        "Request",
        foreign_keys="[Request.selected_rider_id]",
        back_populates="selected_rider"
    )

    ratings = relationship("Rating", back_populates="rider")
    payments = relationship("Payment", back_populates="rider")
    tasks = relationship("RiderTask", back_populates="rider")