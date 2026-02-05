from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class RequestStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    payment_processing = "payment_processing"
    completed = "completed"
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    gcash = "gcash"


class BillRequest(Base):
    __tablename__ = "bill_requests"

    request_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="SET NULL"), nullable=True, index=True)
    biller_name = Column(String(100), nullable=False)
    biller_category = Column(String(50), nullable=False)
    account_number = Column(String(100), nullable=False)
    bill_amount = Column(DECIMAL(10, 2), nullable=False)
    due_date = Column(Date, nullable=True)
    bill_photo_url = Column(String(500), nullable=True)  # Cloudinary URL for bill photo
    request_status = Column(Enum(RequestStatus), default=RequestStatus.pending, index=True)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    service_fee = Column(DECIMAL(10, 2), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    delivery_address = Column(Text, nullable=False)
    contact_number = Column(String(20), nullable=False)
    preferred_time = Column(DateTime, nullable=True)
    special_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("User", back_populates="bill_requests", foreign_keys=[customer_id])
    rider = relationship("Rider", back_populates="bill_requests")
    complaints = relationship("Complaint", back_populates="request")
    payment = relationship("Payment", back_populates="bill_request", uselist=False)
    rating = relationship("Rating", back_populates="bill_request", uselist=False)
    rider_tasks = relationship("RiderTask", back_populates="bill_request")