from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    completed = "completed"
    failed = "failed"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    gcash = "gcash"


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("bill_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="CASCADE"), nullable=False, index=True)
    bill_amount = Column(DECIMAL(10, 2), nullable=False)
    service_fee = Column(DECIMAL(10, 2), nullable=False)
    total_collected = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    gcash_reference_number = Column(String(100), nullable=True)
    gcash_receipt_path = Column(String(255), nullable=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    payment_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    bill_request = relationship("BillRequest", back_populates="payment")
    customer = relationship("User", back_populates="payments")
    rider = relationship("Rider", back_populates="payments")