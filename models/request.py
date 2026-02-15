# models/request.py
# ─────────────────────────────────────────────────────────────
# SQLAlchemy ORM Model for unified requests table
# Handles ALL service types: groceries, bills, delivery, pickup, pharmacy, documents
# ─────────────────────────────────────────────────────────────

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Request(Base):
    """Unified request model - handles all service types"""
    __tablename__ = "requests"

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="SET NULL"), nullable=True)
    
    # Service details
    service_type = Column(
        String(50),  # groceries, bills, delivery, pickup, pharmacy, documents
        nullable=False,
        index=True
    )
    items_description = Column(Text, nullable=False)
    budget_limit = Column(Decimal(10, 2), nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Location details
    pickup_location = Column(String(500), nullable=True)
    delivery_address = Column(String(500), nullable=True)
    delivery_option = Column(String(50), default="current-location")
    
    # Status
    status = Column(
        String(50),  # pending, assigned, in_progress, completed, cancelled
        default="pending",
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Rider selection tracking
    selected_rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="SET NULL"), nullable=True)
    notification_sent_at = Column(DateTime, nullable=True)

    def dict(self):
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "customer_id": self.customer_id,
            "rider_id": self.rider_id,
            "service_type": self.service_type,
            "items_description": self.items_description,
            "budget_limit": float(self.budget_limit) if self.budget_limit else None,
            "special_instructions": self.special_instructions,
            "pickup_location": self.pickup_location,
            "delivery_address": self.delivery_address,
            "delivery_option": self.delivery_option,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }