from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from database import get_db
from models.user import User
from models.request import Request, RequestStatus, ServiceType, RequestBillPhoto, RequestAttachment, PaymentMethod, PaymentStatus
from models.rider import Rider
from utils.dependencies import get_current_active_user
from utils.notification_helper import (
    notify_rider_selected, notify_rider_accepted, notify_delivery_started,
    notify_delivery_completed, notify_bill_submitted, notify_payment_received,
    notify_payment_confirmed, notify_request_cancelled
)
from decimal import Decimal
from sqlalchemy import and_, text
import logging

notif_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requests", tags=["Requests"])


# Helper to safely extract enum value for JSON serialization
def enum_val(v):
    """Return .value if it's an enum, otherwise the value itself (or None)."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else v


# ===== SCHEMAS =====

class BillPhotoResponse(BaseModel):
    photo_id: int
    photo_url: str
    file_name: Optional[str]
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    attachment_id: int
    file_name: str
    file_url: str
    file_type: Optional[str]
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateRequestRequest(BaseModel):
    service_type: ServiceType
    items_description: str
    budget_limit: Optional[float] = None
    special_instructions: Optional[str] = None
    pickup_location: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_option: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    payment_method: Optional[str] = None


class RequestResponse(BaseModel):
    request_id: int
    customer_id: int
    rider_id: Optional[int]
    service_type: str
    items_description: str
    budget_limit: Optional[float]
    special_instructions: Optional[str]
    status: str
    pickup_location: Optional[str]
    delivery_address: Optional[str]
    delivery_option: Optional[str]
    payment_method: Optional[str] = None
    item_cost: Optional[float] = None
    service_fee: Optional[float] = None
    total_amount: Optional[float] = None
    gcash_reference: Optional[str] = None
    gcash_screenshot_url: Optional[str] = None
    payment_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    bill_photos: List[BillPhotoResponse] = []
    attachments: List[AttachmentResponse] = []

    class Config:
        from_attributes = True


class RequestDetailResponse(RequestResponse):
    customer_name: Optional[str]
    customer_phone: Optional[str]
    rider_name: Optional[str]
    rider_phone: Optional[str]


class AddBillPhotoRequest(BaseModel):
    photo_url: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class AddAttachmentRequest(BaseModel):
    file_name: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None


# ===== ENDPOINTS =====

@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_request(
    request_data: CreateRequestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new request (groceries, bills, delivery, pharmacy, pickup, documents)
    """

    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create requests"
        )

    # Validate delivery service specific fields
    if request_data.service_type == ServiceType.delivery:
        if not request_data.pickup_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pickup location is required for delivery service"
            )
        if request_data.delivery_option == "custom-address" and not request_data.delivery_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery address is required when delivery_option is custom-address"
            )

    # Create request
    new_request = Request(
        customer_id=current_user.user_id,
        service_type=request_data.service_type,
        items_description=request_data.items_description,
        budget_limit=Decimal(str(request_data.budget_limit)) if request_data.budget_limit else None,
        special_instructions=request_data.special_instructions,
        pickup_location=request_data.pickup_location,
        delivery_address=request_data.delivery_address,
        delivery_option=request_data.delivery_option,
        payment_method=request_data.payment_method if request_data.payment_method in ('cod', 'gcash') else None,
        status=RequestStatus.pending
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Save customer GPS to user_locations if provided
    if request_data.latitude is not None and request_data.longitude is not None:
        try:
            # Check if recent location exists
            existing = db.execute(
                text("SELECT location_id FROM user_locations WHERE user_id = :uid AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR) ORDER BY created_at DESC LIMIT 1"),
                {"uid": current_user.user_id}
            ).fetchone()
            if existing:
                db.execute(
                    text("UPDATE user_locations SET latitude = :lat, longitude = :lng, created_at = NOW() WHERE location_id = :lid"),
                    {"lat": request_data.latitude, "lng": request_data.longitude, "lid": existing[0]}
                )
            else:
                db.execute(
                    text("INSERT INTO user_locations (user_id, request_id, latitude, longitude) VALUES (:uid, :rid, :lat, :lng)"),
                    {"uid": current_user.user_id, "rid": new_request.request_id, "lat": request_data.latitude, "lng": request_data.longitude}
                )
            db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to save customer GPS on create: {e}")

    return {
        "success": True,
        "message": "Request created successfully",
        "data": {
            "request_id": new_request.request_id,
            "status": new_request.status,
            "service_type": new_request.service_type,
            "created_at": new_request.created_at.isoformat()
        }
    }


@router.get("/my-requests")
def get_my_requests(
    service_type: Optional[ServiceType] = None,
    status_filter: Optional[RequestStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's requests
    """

    if current_user.user_type == "customer":
        query = db.query(Request).filter(Request.customer_id == current_user.user_id)
    elif current_user.user_type == "rider":
        query = db.query(Request).filter(Request.rider_id == current_user.rider_profile.rider_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view requests"
        )

    if service_type:
        query = query.filter(Request.service_type == service_type)

    if status_filter:
        query = query.filter(Request.status == status_filter)

    total = query.count()

    requests = query.order_by(Request.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    result_data = []
    for req in requests:
        item = {
            "request_id": req.request_id,
            "service_type": req.service_type,
            "items_description": req.items_description[:100],
            "status": req.status,
            "budget_limit": float(req.budget_limit) if req.budget_limit else None,
            "created_at": req.created_at.isoformat(),
            "rider_id": req.rider_id
        }
        # Include customer name for riders
        if current_user.user_type == "rider":
            customer = db.query(User).filter(User.user_id == req.customer_id).first()
            item["customer_name"] = customer.full_name if customer else "Customer"
        result_data.append(item)

    return {
        "success": True,
        "message": "Requests retrieved successfully",
        "data": result_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


# ===== STATIC ROUTES MUST COME BEFORE /{request_id} =====

@router.get("/pending-for-me")
def get_pending_requests_for_rider(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get requests where THIS rider has been selected by customers.
    Only shows requests in 'pending' status that haven't timed out.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can view pending requests"
        )

    rider = current_user.rider_profile
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider profile not found"
        )

    timeout_threshold = datetime.utcnow() - timedelta(minutes=10)

    requests = db.query(Request).filter(
        and_(
            Request.selected_rider_id == rider.rider_id,
            Request.status == RequestStatus.pending,
            Request.notification_sent_at > timeout_threshold
        )
    ).order_by(Request.notification_sent_at.desc()).all()

    result = []
    for req in requests:
        customer = db.query(User).filter(User.user_id == req.customer_id).first()

        time_elapsed = (datetime.utcnow() - req.notification_sent_at).total_seconds()
        time_remaining = max(0, 600 - int(time_elapsed))

        result.append({
            "request_id": req.request_id,
            "service_type": req.service_type,
            "items_description": req.items_description,
            "budget_limit": float(req.budget_limit) if req.budget_limit else None,
            "special_instructions": req.special_instructions,
            "pickup_location": req.pickup_location,
            "delivery_address": req.delivery_address,
            "delivery_option": req.delivery_option,
            "payment_method": enum_val(req.payment_method),
            "customer_name": customer.full_name if customer else "Unknown",
            "customer_phone": customer.phone_number if customer else None,
            "created_at": req.created_at.isoformat(),
            "notification_sent_at": req.notification_sent_at.isoformat() if req.notification_sent_at else None,
            "time_remaining_seconds": time_remaining
        })

    return {
        "success": True,
        "message": f"Found {len(result)} pending requests",
        "data": result
    }


# ===== PARAMETERIZED ROUTES BELOW =====

@router.get("/{request_id}")
def get_request_details(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get request details with bill photos and attachments
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if current_user.user_type == "customer" and request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )

    if current_user.user_type == "rider" and request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )

    customer = db.query(User).filter(User.user_id == request.customer_id).first()

    rider_name = None
    rider_phone = None
    if request.rider_id:
        rider = db.query(Rider).filter(Rider.rider_id == request.rider_id).first()
        if rider and rider.user:
            rider_name = rider.user.full_name
            rider_phone = rider.user.phone_number

    # Get customer's latest GPS location
    customer_location = None
    loc_row = db.execute(
        text("SELECT latitude, longitude, address FROM user_locations WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": request.customer_id}
    ).fetchone()
    if loc_row:
        customer_location = {
            "latitude": float(loc_row[0]),
            "longitude": float(loc_row[1]),
            "address": loc_row[2]
        }

    return {
        "success": True,
        "message": "Request retrieved successfully",
        "data": {
            "request_id": request.request_id,
            "customer_id": request.customer_id,
            "customer_name": customer.full_name if customer else None,
            "customer_phone": customer.phone_number if customer else None,
            "customer_location": customer_location,
            "rider_id": request.rider_id,
            "rider_name": rider_name,
            "rider_phone": rider_phone,
            "service_type": enum_val(request.service_type),
            "items_description": request.items_description,
            "budget_limit": float(request.budget_limit) if request.budget_limit else None,
            "special_instructions": request.special_instructions,
            "status": enum_val(request.status),
            "pickup_location": request.pickup_location,
            "delivery_address": request.delivery_address,
            "delivery_option": request.delivery_option,
            "payment_method": enum_val(request.payment_method),
            "item_cost": float(request.item_cost) if request.item_cost else None,
            "service_fee": float(request.service_fee) if request.service_fee else None,
            "total_amount": float(request.total_amount) if request.total_amount else None,
            "gcash_reference": request.gcash_reference,
            "gcash_screenshot_url": request.gcash_screenshot_url,
            "payment_status": enum_val(request.payment_status),
            "payment_proof_url": request.payment_proof_url,
            "created_at": request.created_at.isoformat(),
            "updated_at": request.updated_at.isoformat(),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "bill_photos": [
                {
                    "photo_id": photo.photo_id,
                    "photo_url": photo.photo_url,
                    "file_name": photo.file_name,
                    "file_size": photo.file_size,
                    "created_at": photo.created_at.isoformat()
                }
                for photo in request.bill_photos
            ],
            "attachments": [
                {
                    "attachment_id": att.attachment_id,
                    "file_name": att.file_name,
                    "file_url": att.file_url,
                    "file_type": att.file_type,
                    "file_size": att.file_size,
                    "created_at": att.created_at.isoformat()
                }
                for att in request.attachments
            ]
        }
    }


@router.post("/{request_id}/add-bill-photo")
def add_bill_photo(
    request_id: int,
    photo_data: AddBillPhotoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add bill photo to request (accepts JSON body)
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add photos to this request"
        )

    bill_photo = RequestBillPhoto(
        request_id=request_id,
        photo_url=photo_data.photo_url,
        file_name=photo_data.file_name,
        file_size=photo_data.file_size
    )

    db.add(bill_photo)
    db.commit()
    db.refresh(bill_photo)

    return {
        "success": True,
        "message": "Bill photo added successfully",
        "data": {
            "photo_id": bill_photo.photo_id,
            "photo_url": bill_photo.photo_url
        }
    }


@router.post("/{request_id}/add-attachment")
def add_attachment(
    request_id: int,
    attachment_data: AddAttachmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add file attachment to request (accepts JSON body)
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add attachments to this request"
        )

    attachment = RequestAttachment(
        request_id=request_id,
        file_name=attachment_data.file_name,
        file_url=attachment_data.file_url,
        file_type=attachment_data.file_type,
        file_size=attachment_data.file_size
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "success": True,
        "message": "Attachment added successfully",
        "data": {
            "attachment_id": attachment.attachment_id,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url
        }
    }


@router.post("/{request_id}/accept")
def accept_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Accept a request (RIDER ONLY)
    Changes status from 'pending' to 'assigned'
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can accept requests"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept request with status: {request.status}"
        )

    request.rider_id = current_user.rider_profile.rider_id
    request.status = RequestStatus.assigned
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Notify customer that rider accepted
    try:
        notify_rider_accepted(db, request.customer_id, request.request_id, current_user.full_name)
    except Exception as e:
        notif_logger.warning(f"Failed to create acceptance notification: {e}")

    return {
        "success": True,
        "message": "Request accepted successfully",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status),
            "rider_id": request.rider_id
        }
    }


@router.patch("/{request_id}/status")
def update_request_status(
    request_id: int,
    new_status: RequestStatus,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update request status
    Status flow: pending → assigned → in_progress → completed
    Any status → cancelled (except completed)
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if current_user.user_type == "customer" and request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this request"
        )

    if current_user.user_type == "rider" and request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this request"
        )

    if request.status == RequestStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of completed request"
        )

    old_status = request.status
    request.status = new_status
    request.updated_at = datetime.utcnow()

    if new_status == RequestStatus.completed:
        request.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    return {
        "success": True,
        "message": f"Request status updated from {old_status} to {new_status}",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status),
            "updated_at": request.updated_at.isoformat()
        }
    }


@router.post("/{request_id}/cancel")
def cancel_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a request
    Only customers can cancel their own requests
    Cannot cancel if already completed
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this request"
        )

    if request.status == RequestStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed request"
        )

    request.status = RequestStatus.cancelled
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    return {
        "success": True,
        "message": "Request cancelled successfully",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status)
        }
    }


@router.delete("/{request_id}/photos/{photo_id}")
def delete_bill_photo(
    request_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a bill photo from request"""

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    photo = db.query(RequestBillPhoto).filter(RequestBillPhoto.photo_id == photo_id).first()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    db.delete(photo)
    db.commit()

    return {
        "success": True,
        "message": "Photo deleted successfully"
    }


@router.delete("/{request_id}/attachments/{attachment_id}")
def delete_attachment(
    request_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an attachment from request"""

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    attachment = db.query(RequestAttachment).filter(RequestAttachment.attachment_id == attachment_id).first()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )

    db.delete(attachment)
    db.commit()

    return {
        "success": True,
        "message": "Attachment deleted successfully"
    }


@router.post("/{request_id}/select-rider")
def select_rider_for_request(
    request_id: int,
    rider_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Customer selects a specific rider for their request.
    This sends a notification to ONLY that rider.
    """

    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can select riders"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this request"
        )

    if request.status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already has status: {request.status}"
        )

    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider not found"
        )

    request.selected_rider_id = rider_id
    request.notification_sent_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Create notification for the selected rider
    try:
        notify_rider_selected(db, rider.user_id, request.request_id, current_user.full_name, enum_val(request.service_type))
    except Exception as e:
        notif_logger.warning(f"Failed to create rider notification: {e}")

    return {
        "success": True,
        "message": f"Rider {rider.user.full_name} has been notified",
        "data": {
            "request_id": request.request_id,
            "selected_rider_id": rider_id,
            "rider_name": rider.user.full_name,
            "notification_sent_at": request.notification_sent_at.isoformat()
        }
    }


@router.post("/{request_id}/decline")
def decline_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rider declines a request they were selected for.
    Returns request to pending state so customer can select another rider.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can decline requests"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.selected_rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You were not selected for this request"
        )

    request.selected_rider_id = None
    request.notification_sent_at = None
    request.updated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "message": "Request declined. Customer will be notified.",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status)
        }
    }


@router.post("/{request_id}/start-delivery")
def start_delivery(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rider marks they're done shopping/collecting and starting delivery.
    Changes status from 'assigned' to 'in_progress'.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can start delivery"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized - this request is not assigned to you"
        )

    if request.status != RequestStatus.assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start delivery on request with status: {request.status}"
        )

    request.status = RequestStatus.in_progress
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Notify customer that delivery started
    try:
        notify_delivery_started(db, request.customer_id, request.request_id, current_user.full_name)
    except Exception as e:
        notif_logger.warning(f"Failed to create delivery started notification: {e}")

    # Get customer's latest GPS location for the rider
    customer_location = None
    loc_row = db.execute(
        text("SELECT latitude, longitude, address FROM user_locations WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": request.customer_id}
    ).fetchone()
    if loc_row:
        customer_location = {
            "latitude": float(loc_row[0]),
            "longitude": float(loc_row[1]),
            "address": loc_row[2]
        }

    customer = db.query(User).filter(User.user_id == request.customer_id).first()

    return {
        "success": True,
        "message": "Delivery started! Customer has been notified.",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status),
            "updated_at": request.updated_at.isoformat(),
            "customer_name": customer.full_name if customer else None,
            "customer_location": customer_location,
            "delivery_address": request.delivery_address,
            "pickup_location": request.pickup_location,
            "delivery_option": request.delivery_option
        }
    }


# ===== PAYMENT ENDPOINTS =====

class SubmitBillRequest(BaseModel):
    item_cost: float
    service_fee: float


class SubmitGcashPaymentRequest(BaseModel):
    gcash_reference: str
    gcash_screenshot_url: Optional[str] = None


@router.post("/{request_id}/submit-bill")
def submit_bill(
    request_id: int,
    bill_data: SubmitBillRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rider submits the bill breakdown (item cost + service fee).
    This tells the customer how much to pay.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can submit bills"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized - this request is not assigned to you"
        )

    if request.status not in [RequestStatus.assigned, RequestStatus.in_progress]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit bill for request with status: {request.status}"
        )

    item_cost = Decimal(str(bill_data.item_cost))
    service_fee = Decimal(str(bill_data.service_fee))
    total = item_cost + service_fee

    request.item_cost = item_cost
    request.service_fee = service_fee
    request.total_amount = total
    request.payment_status = PaymentStatus.pending
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Notify customer about the bill
    try:
        notify_bill_submitted(db, request.customer_id, request.request_id, float(total))
    except Exception as e:
        notif_logger.warning(f"Failed to create bill notification: {e}")

    return {
        "success": True,
        "message": "Bill submitted successfully. Customer has been notified.",
        "data": {
            "request_id": request.request_id,
            "item_cost": float(request.item_cost),
            "service_fee": float(request.service_fee),
            "total_amount": float(request.total_amount),
            "payment_method": enum_val(request.payment_method),
            "payment_status": enum_val(request.payment_status)
        }
    }


@router.post("/{request_id}/submit-payment")
def submit_payment(
    request_id: int,
    payment_data: SubmitGcashPaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Customer submits GCash payment (reference number + optional screenshot).
    Only for GCash payment method.
    """

    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can submit payments"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit payment for this request"
        )

    if request.payment_method != PaymentMethod.gcash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GCash payment submission is only for GCash payment method"
        )

    if not request.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rider has not submitted the bill yet"
        )

    request.gcash_reference = payment_data.gcash_reference
    if payment_data.gcash_screenshot_url:
        request.gcash_screenshot_url = payment_data.gcash_screenshot_url
    request.payment_status = PaymentStatus.submitted
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Notify rider about payment
    try:
        rider = db.query(Rider).filter(Rider.rider_id == request.rider_id).first()
        if rider:
            notify_payment_received(db, rider.user_id, request.request_id, float(request.total_amount or 0))
    except Exception as e:
        notif_logger.warning(f"Failed to create payment notification: {e}")

    return {
        "success": True,
        "message": "GCash payment submitted. Rider will verify.",
        "data": {
            "request_id": request.request_id,
            "gcash_reference": request.gcash_reference,
            "payment_status": enum_val(request.payment_status)
        }
    }


@router.post("/{request_id}/confirm-payment")
def confirm_payment(
    request_id: int,
    body: dict = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rider confirms payment has been received (GCash verified or COD collected).
    Requires proof of payment photo URL.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can confirm payment"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized - this request is not assigned to you"
        )

    # Save proof of payment URL if provided
    if body and body.get("payment_proof_url"):
        request.payment_proof_url = body["payment_proof_url"]

    request.payment_status = PaymentStatus.confirmed
    request.updated_at = datetime.utcnow()

    # Notify customer about payment confirmation
    try:
        notify_payment_confirmed(db, request.customer_id, request.request_id)
    except Exception as e:
        notif_logger.warning(f"Failed to create payment confirmation notification: {e}")

    # Auto-complete delivery when payment is confirmed
    # (confirming payment means rider has delivered & collected payment — task is done)
    # Allow auto-complete from both 'assigned' and 'in_progress' statuses
    delivery_auto_completed = False
    if request.status in [RequestStatus.assigned, RequestStatus.in_progress]:
        request.status = RequestStatus.completed
        request.completed_at = datetime.utcnow()
        delivery_auto_completed = True

    db.commit()
    db.refresh(request)

    msg = "Payment confirmed!"
    if delivery_auto_completed:
        msg = "Payment confirmed and delivery completed!"

    return {
        "success": True,
        "message": msg,
        "data": {
            "request_id": request.request_id,
            "payment_status": enum_val(request.payment_status),
            "status": enum_val(request.status),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "delivery_auto_completed": delivery_auto_completed,
            "total_amount": float(request.total_amount) if request.total_amount else None,
            "payment_proof_url": request.payment_proof_url
        }
    }


@router.post("/{request_id}/complete-delivery")
def complete_delivery(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rider marks delivery as completed.
    Changes status from 'in_progress' to 'completed'.
    """

    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can complete delivery"
        )

    request = db.query(Request).filter(Request.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized - this request is not assigned to you"
        )

    # Allow completing from both 'assigned' and 'in_progress' statuses
    # Riders may skip "Start Delivery" and go directly to "Complete Delivery"
    if request.status not in [RequestStatus.assigned, RequestStatus.in_progress]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete delivery on request with status: {request.status}"
        )

    request.status = RequestStatus.completed
    request.completed_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Notify customer about delivery completion
    try:
        notify_delivery_completed(db, request.customer_id, request.request_id)
    except Exception as e:
        notif_logger.warning(f"Failed to create delivery completion notification: {e}")

    return {
        "success": True,
        "message": "Delivery completed successfully!",
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status),
            "completed_at": request.completed_at.isoformat()
        }
    }


@router.get("/{request_id}/status-poll")
def poll_request_status(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lightweight endpoint for customers to poll request status.
    Returns just the essential info to check if rider accepted.
    """

    request = db.query(Request).filter(Request.request_id == request_id).first()
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if current_user.user_type == "customer" and request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    timed_out = False
    if request.notification_sent_at:
        time_elapsed = (datetime.utcnow() - request.notification_sent_at).total_seconds()
        if time_elapsed > 600 and request.status == RequestStatus.pending:
            timed_out = True
            request.selected_rider_id = None
            request.notification_sent_at = None
            db.commit()

    rider_info = None
    if request.rider_id:
        rider = db.query(Rider).filter(Rider.rider_id == request.rider_id).first()
        if rider and rider.user:
            rider_info = {
                "rider_id": rider.rider_id,
                "name": rider.user.full_name,
                "phone": rider.user.phone_number,
                "vehicle_type": rider.vehicle_type,
                "license_plate": rider.vehicle_plate,
                "rating": float(rider.rating) if rider.rating else 0
            }

    return {
        "success": True,
        "data": {
            "request_id": request.request_id,
            "status": enum_val(request.status),
            "rider_id": request.rider_id,
            "selected_rider_id": request.selected_rider_id,
            "timed_out": timed_out,
            "rider_info": rider_info,
            "payment_method": enum_val(request.payment_method),
            "item_cost": float(request.item_cost) if request.item_cost else None,
            "service_fee": float(request.service_fee) if request.service_fee else None,
            "total_amount": float(request.total_amount) if request.total_amount else None,
            "gcash_reference": request.gcash_reference,
            "payment_status": enum_val(request.payment_status),
            "updated_at": request.updated_at.isoformat()
        }
    }