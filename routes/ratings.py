# routes/ratings.py
# Rating system for Pasugo - customers rate riders after delivery completion

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from database import get_db
from models.user import User
from models.rider import Rider
from models.request import Request, RequestStatus
from models.notification import Notification, NotificationType
from utils.dependencies import get_current_active_user

router = APIRouter(prefix="/ratings", tags=["Ratings"])


# ===== SCHEMAS =====

class SubmitRatingRequest(BaseModel):
    request_id: int
    overall_rating: float = Field(..., ge=1, le=5)
    communication_rating: Optional[float] = Field(None, ge=1, le=5)
    speed_rating: Optional[float] = Field(None, ge=1, le=5)
    service_rating: Optional[float] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None
    is_anonymous: bool = False


# ===== ENDPOINTS =====

@router.post("/submit")
def submit_rating(
    rating_data: SubmitRatingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Customer submits a rating for a completed delivery"""

    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can submit ratings"
        )

    # Get the request
    request = db.query(Request).filter(Request.request_id == rating_data.request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.customer_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your request")

    if request.status != RequestStatus.completed:
        raise HTTPException(status_code=400, detail="Can only rate completed deliveries")

    if not request.rider_id:
        raise HTTPException(status_code=400, detail="No rider assigned to this request")

    # Check if already rated
    from sqlalchemy import text
    existing = db.execute(
        text("SELECT rating_id FROM rider_ratings WHERE request_id = :rid AND customer_id = :cid"),
        {"rid": rating_data.request_id, "cid": current_user.user_id}
    ).fetchone()

    if existing:
        raise HTTPException(status_code=400, detail="You have already rated this delivery")

    # Insert the rating
    now = datetime.utcnow()
    result = db.execute(
        text("""
            INSERT INTO rider_ratings (request_id, rider_id, customer_id, overall_rating, is_anonymous, rating_date, created_at)
            VALUES (:request_id, :rider_id, :customer_id, :overall_rating, :is_anonymous, :rating_date, :created_at)
        """),
        {
            "request_id": rating_data.request_id,
            "rider_id": request.rider_id,
            "customer_id": current_user.user_id,
            "overall_rating": rating_data.overall_rating,
            "is_anonymous": rating_data.is_anonymous,
            "rating_date": now,
            "created_at": now
        }
    )
    db.commit()
    rating_id = result.lastrowid

    # Insert category ratings if provided
    categories = []
    if rating_data.communication_rating:
        categories.append(("communication", rating_data.communication_rating))
    if rating_data.speed_rating:
        categories.append(("speed", rating_data.speed_rating))
    if rating_data.service_rating:
        categories.append(("service_quality", rating_data.service_rating))

    for cat_name, cat_score in categories:
        db.execute(
            text("""
                INSERT INTO rating_categories (rating_id, category_name, category_rating)
                VALUES (:rating_id, :category_name, :category_rating)
            """),
            {"rating_id": rating_id, "category_name": cat_name, "category_rating": cat_score}
        )

    # Insert feedback if provided
    if rating_data.feedback_text:
        # Determine feedback type based on overall rating
        if rating_data.overall_rating >= 4:
            feedback_type = "positive"
        elif rating_data.overall_rating >= 3:
            feedback_type = "neutral"
        else:
            feedback_type = "negative"

        db.execute(
            text("""
                INSERT INTO rider_feedback (rating_id, task_id, rider_id, customer_id, feedback_text, feedback_type, feedback_date, created_at)
                VALUES (:rating_id, :task_id, :rider_id, :customer_id, :feedback_text, :feedback_type, :feedback_date, :created_at)
            """),
            {
                "rating_id": rating_id,
                "task_id": None,
                "rider_id": request.rider_id,
                "customer_id": current_user.user_id,
                "feedback_text": rating_data.feedback_text,
                "feedback_type": feedback_type,
                "feedback_date": now,
                "created_at": now
            }
        )

    db.commit()

    # Update rider average rating
    avg_result = db.execute(
        text("SELECT AVG(overall_rating) as avg_rating, COUNT(*) as total FROM rider_ratings WHERE rider_id = :rid"),
        {"rid": request.rider_id}
    ).fetchone()

    if avg_result and avg_result[0]:
        new_avg = round(float(avg_result[0]), 2)
        db.execute(
            text("UPDATE riders SET rating = :rating WHERE rider_id = :rid"),
            {"rating": new_avg, "rid": request.rider_id}
        )
        db.commit()

    # Create notification for rider
    rider = db.query(Rider).filter(Rider.rider_id == request.rider_id).first()
    if rider:
        notification = Notification(
            user_id=rider.user_id,
            notification_type=NotificationType.delivery_update,
            title="New Rating Received",
            message=f"You received a {rating_data.overall_rating}-star rating for your delivery!",
            reference_id=rating_data.request_id,
            reference_type="request"
        )
        db.add(notification)
        db.commit()

    return {
        "success": True,
        "message": "Rating submitted successfully!",
        "data": {
            "rating_id": rating_id,
            "overall_rating": rating_data.overall_rating,
            "request_id": rating_data.request_id
        }
    }


@router.get("/rider/{rider_id}")
def get_rider_ratings(
    rider_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get ratings for a specific rider"""
    from sqlalchemy import text

    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    ratings = db.execute(
        text("""
            SELECT rr.rating_id, rr.overall_rating, rr.is_anonymous, rr.rating_date,
                   u.full_name as customer_name,
                   rf.feedback_text
            FROM rider_ratings rr
            LEFT JOIN users u ON rr.customer_id = u.user_id
            LEFT JOIN rider_feedback rf ON rr.rating_id = rf.rating_id
            WHERE rr.rider_id = :rider_id
            ORDER BY rr.rating_date DESC
            LIMIT 50
        """),
        {"rider_id": rider_id}
    ).fetchall()

    ratings_list = []
    for r in ratings:
        ratings_list.append({
            "rating_id": r[0],
            "overall_rating": float(r[1]),
            "is_anonymous": bool(r[2]),
            "rating_date": r[3].isoformat() if r[3] else None,
            "customer_name": "Anonymous" if r[2] else r[4],
            "feedback_text": r[5]
        })

    return {
        "success": True,
        "data": {
            "rider_id": rider_id,
            "average_rating": float(rider.rating) if rider.rating else 0,
            "total_ratings": len(ratings_list),
            "ratings": ratings_list
        }
    }


@router.get("/my-ratings")
def get_my_ratings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get ratings for the current rider"""
    from sqlalchemy import text

    if current_user.user_type != "rider":
        raise HTTPException(status_code=403, detail="Only riders can view their ratings")

    rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider profile not found")

    ratings = db.execute(
        text("""
            SELECT rr.rating_id, rr.overall_rating, rr.is_anonymous, rr.rating_date,
                   u.full_name as customer_name,
                   rf.feedback_text,
                   rr.request_id
            FROM rider_ratings rr
            LEFT JOIN users u ON rr.customer_id = u.user_id
            LEFT JOIN rider_feedback rf ON rr.rating_id = rf.rating_id
            WHERE rr.rider_id = :rider_id
            ORDER BY rr.rating_date DESC
            LIMIT 50
        """),
        {"rider_id": rider.rider_id}
    ).fetchall()

    ratings_list = []
    for r in ratings:
        ratings_list.append({
            "rating_id": r[0],
            "overall_rating": float(r[1]),
            "is_anonymous": bool(r[2]),
            "rating_date": r[3].isoformat() if r[3] else None,
            "customer_name": "Anonymous" if r[2] else r[4],
            "feedback_text": r[5],
            "request_id": r[6]
        })

    return {
        "success": True,
        "data": {
            "rider_id": rider.rider_id,
            "average_rating": float(rider.rating) if rider.rating else 0,
            "total_ratings": len(ratings_list),
            "ratings": ratings_list
        }
    }


@router.get("/check/{request_id}")
def check_rating_exists(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if current user already rated a specific request"""
    from sqlalchemy import text

    existing = db.execute(
        text("SELECT rating_id, overall_rating FROM rider_ratings WHERE request_id = :rid AND customer_id = :cid"),
        {"rid": request_id, "cid": current_user.user_id}
    ).fetchone()

    return {
        "success": True,
        "data": {
            "has_rated": existing is not None,
            "rating_id": existing[0] if existing else None,
            "overall_rating": float(existing[1]) if existing else None
        }
    }
