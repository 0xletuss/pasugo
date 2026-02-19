from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.notification import Notification
from utils.dependencies import get_current_active_user
from utils.cache import cache
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def get_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's notifications"""
    
    cache_key = f"notifications:list:{current_user.user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    notifications = db.query(Notification) \
        .filter(Notification.user_id == current_user.user_id) \
        .order_by(Notification.created_at.desc()) \
        .limit(50) \
        .all()
    
    result = {
        "success": True,
        "message": "Notifications retrieved successfully",
        "data": [
            {
                "notification_id": n.notification_id,
                "notification_type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ]
    }
    cache.set(cache_key, result, ttl=10)
    return result


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    
    cache_key = f"notifications:unread:{current_user.user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    count = db.query(Notification) \
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ) \
        .count()
    
    result = {
        "success": True,
        "message": "Unread count retrieved successfully",
        "data": {
            "unread_count": count
        }
    }
    cache.set(cache_key, result, ttl=10)
    return result


@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    
    db.commit()
    
    # Invalidate notification caches for this user
    cache.delete(f"notifications:unread:{current_user.user_id}")
    cache.delete(f"notifications:list:{current_user.user_id}")
    
    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.patch("/mark-all-read")
def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    
    db.query(Notification) \
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False
        ) \
        .update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
    
    db.commit()
    
    # Invalidate notification caches for this user
    cache.delete(f"notifications:unread:{current_user.user_id}")
    cache.delete(f"notifications:list:{current_user.user_id}")
    
    return {
        "success": True,
        "message": "All notifications marked as read"
    }