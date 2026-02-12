from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ServiceType(str, enum.Enum):
    groceries = "groceries"
    bills = "bills"
    delivery = "delivery"
    pharmacy = "pharmacy"
    pickup = "pickup"
    documents = "documents"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Request(Base):
    __tablename__ = "requests"

    request_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Service details
    service_type = Column(Enum(ServiceType), nullable=False, index=True)
    items_description = Column(Text, nullable=False)
    budget_limit = Column(DECIMAL(10, 2), nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Request status
    status = Column(Enum(RequestStatus), default=RequestStatus.pending, index=True)
    
    # Location details (for delivery service)
    pickup_location = Column(String(500), nullable=True)
    delivery_address = Column(String(500), nullable=True)
    delivery_option = Column(String(50), nullable=True)  # 'current-location' or 'custom-address'
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("User", back_populates="requests", foreign_keys=[customer_id])
    rider = relationship("Rider", back_populates="requests")
    bill_photos = relationship("RequestBillPhoto", back_populates="request", cascade="all, delete-orphan")
    attachments = relationship("RequestAttachment", back_populates="request", cascade="all, delete-orphan")


class RequestBillPhoto(Base):
    __tablename__ = "request_bill_photos"

    photo_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    
    photo_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    request = relationship("Request", back_populates="bill_photos")


class RequestAttachment(Base):
    __tablename__ = "request_attachments"

    attachment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    request = relationship("Request", back_populates="attachments")