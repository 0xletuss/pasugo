"""
models/remittance.py  –  Daily rider remittance tracking

At end-of-day every rider physically remits the admin's 30 % share.
Each record = one rider × one date.
"""

from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime, Date,
    DECIMAL, Boolean, String, Text, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class RemittanceStatus(str, enum.Enum):
    pending   = "pending"      # rider hasn't come to office yet
    remitted  = "remitted"     # admin received the cash
    waived    = "waived"       # admin chose to waive (rare)


class Remittance(Base):
    __tablename__ = "remittances"

    remittance_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rider_id      = Column(Integer, ForeignKey("riders.rider_id", ondelete="CASCADE"), nullable=False, index=True)
    remittance_date = Column(Date, nullable=False, index=True)

    # Snapshot of that day's numbers
    total_deliveries  = Column(Integer, default=0)
    total_service_fee = Column(DECIMAL(10, 2), default=0)
    rider_share       = Column(DECIMAL(10, 2), default=0)   # 70 %
    admin_share       = Column(DECIMAL(10, 2), default=0)   # 30 %

    # Remittance tracking
    status        = Column(SAEnum(RemittanceStatus), default=RemittanceStatus.pending, index=True)
    remitted_at   = Column(DateTime, nullable=True)
    received_by   = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    rider    = relationship("Rider", backref="remittances")
    receiver = relationship("User", foreign_keys=[received_by])
