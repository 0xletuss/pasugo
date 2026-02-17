# utils/notification_helper.py
# Helper to create notifications for various events

from sqlalchemy.orm import Session
from models.notification import Notification, NotificationType


def create_notification(db: Session, user_id: int, notification_type: str, title: str, message: str, reference_id: int = None, reference_type: str = None):
    """Create a notification for a user"""
    notif = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        reference_id=reference_id,
        reference_type=reference_type
    )
    db.add(notif)
    db.commit()
    return notif


def notify_rider_selected(db: Session, rider_user_id: int, request_id: int, customer_name: str, service_type: str):
    """Notify rider they have been selected for a request"""
    return create_notification(
        db=db,
        user_id=rider_user_id,
        notification_type="request_update",
        title="New Request For You!",
        message=f"{customer_name} selected you for a {service_type} request. Accept within 10 minutes!",
        reference_id=request_id,
        reference_type="request"
    )


def notify_rider_accepted(db: Session, customer_user_id: int, request_id: int, rider_name: str):
    """Notify customer that rider accepted their request"""
    return create_notification(
        db=db,
        user_id=customer_user_id,
        notification_type="request_update",
        title="Rider Accepted!",
        message=f"{rider_name} has accepted your request and is on the way!",
        reference_id=request_id,
        reference_type="request"
    )


def notify_delivery_started(db: Session, customer_user_id: int, request_id: int, rider_name: str):
    """Notify customer that delivery has started"""
    return create_notification(
        db=db,
        user_id=customer_user_id,
        notification_type="delivery_update",
        title="Delivery Started!",
        message=f"{rider_name} has started delivering your items!",
        reference_id=request_id,
        reference_type="request"
    )


def notify_delivery_completed(db: Session, customer_user_id: int, request_id: int):
    """Notify customer that delivery is completed"""
    return create_notification(
        db=db,
        user_id=customer_user_id,
        notification_type="delivery_update",
        title="Delivery Completed!",
        message="Your delivery has been completed. Please rate your rider!",
        reference_id=request_id,
        reference_type="request"
    )


def notify_bill_submitted(db: Session, customer_user_id: int, request_id: int, total_amount: float):
    """Notify customer that rider submitted the bill"""
    return create_notification(
        db=db,
        user_id=customer_user_id,
        notification_type="payment_confirmation",
        title="Bill Submitted",
        message=f"Your rider submitted the bill. Total: ₱{total_amount:.2f}. Please review and pay.",
        reference_id=request_id,
        reference_type="request"
    )


def notify_payment_received(db: Session, rider_user_id: int, request_id: int, amount: float):
    """Notify rider that payment was submitted"""
    return create_notification(
        db=db,
        user_id=rider_user_id,
        notification_type="payment_confirmation",
        title="Payment Submitted",
        message=f"Customer submitted payment of ₱{amount:.2f}. Please confirm.",
        reference_id=request_id,
        reference_type="request"
    )


def notify_payment_confirmed(db: Session, customer_user_id: int, request_id: int):
    """Notify customer that rider confirmed payment"""
    return create_notification(
        db=db,
        user_id=customer_user_id,
        notification_type="payment_confirmation",
        title="Payment Confirmed!",
        message="Your payment has been confirmed by the rider. Thank you!",
        reference_id=request_id,
        reference_type="request"
    )


def notify_request_cancelled(db: Session, user_id: int, request_id: int, cancelled_by: str):
    """Notify about request cancellation"""
    return create_notification(
        db=db,
        user_id=user_id,
        notification_type="request_update",
        title="Request Cancelled",
        message=f"The request has been cancelled by the {cancelled_by}.",
        reference_id=request_id,
        reference_type="request"
    )
