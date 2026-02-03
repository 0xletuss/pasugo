from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, DECIMAL, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Rating(Base):
    __tablename__ = "rider_ratings"

    rating_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("rider_tasks.task_id", ondelete="CASCADE"), nullable=False)
    request_id = Column(Integer, ForeignKey("bill_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("riders.rider_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    overall_rating = Column(DECIMAL(2, 1), nullable=False)
    is_anonymous = Column(Boolean, default=False)
    rating_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    bill_request = relationship("BillRequest", back_populates="rating")
    rider = relationship("Rider", back_populates="ratings")
    customer = relationship("User", back_populates="ratings_given")