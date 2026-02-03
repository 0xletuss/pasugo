from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ComplaintStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("bill_requests.request_id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    complaint_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.open, index=True)
    attachment_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    request = relationship("BillRequest", back_populates="complaints")
    customer = relationship("User", back_populates="complaints")
    replies = relationship("ComplaintReply", back_populates="complaint")


class ComplaintReply(Base):
    __tablename__ = "complaint_replies"

    reply_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(Integer, nullable=True)
    reply_message = Column(Text, nullable=False)
    attachment_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    complaint = relationship("Complaint", back_populates="replies")