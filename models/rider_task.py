from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class TaskType(str, enum.Enum):
    collect_payment = "collect_payment"
    pay_bill = "pay_bill"
    deliver_receipt = "deliver_receipt"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class RiderTask(Base):
    __tablename__ = "rider_tasks"

    task_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("bill_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(Enum(TaskType), nullable=False)
    task_status = Column(Enum(TaskStatus), default=TaskStatus.pending, index=True)
    assigned_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    rider_location = Column(String(255), nullable=True)
    task_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    bill_request = relationship("BillRequest", back_populates="rider_tasks")
    rider = relationship("Rider", back_populates="tasks")
