from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from models.user import User
from models.request import Request, RequestStatus, ServiceType, RequestBillPhoto, RequestAttachment
from models.rider import Rider
from utils.dependencies import get_current_active_user
from decimal import Decimal

router = APIRouter(prefix="/requests", tags=["Requests"])


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


# ===== ENDPOINTS =====

@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_request(
    request_data: CreateRequestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new request (groceries, bills, delivery, pharmacy, pickup, documents)
    
    Frontend sends:
    {
        "service_type": "groceries",
        "items_description": "2kg rice, 1L milk, 5 eggs",
        "budget_limit": 1500.00,
        "special_instructions": "No plastic bags please",
        "pickup_location": null (for delivery service only),
        "delivery_address": null (for delivery service only),
        "delivery_option": null
    }
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
        status=RequestStatus.pending
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
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
    
    Query params:
    - service_type: Filter by service type (optional)
    - status: Filter by status (optional)
    - page: Page number (default 1)
    - page_size: Results per page (default 20, max 100)
    """
    
    if current_user.user_type == "customer":
        query = db.query(Request).filter(Request.customer_id == current_user.user_id)
    elif current_user.user_type == "rider":
        # Riders can see assigned requests
        query = db.query(Request).filter(Request.rider_id == current_user.rider_profile.rider_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view requests"
        )
    
    # Apply filters
    if service_type:
        query = query.filter(Request.service_type == service_type)
    
    if status_filter:
        query = query.filter(Request.status == status_filter)
    
    total = query.count()
    
    requests = query.order_by(Request.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "success": True,
        "message": "Requests retrieved successfully",
        "data": [
            {
                "request_id": req.request_id,
                "service_type": req.service_type,
                "items_description": req.items_description[:100],  # Preview
                "status": req.status,
                "budget_limit": float(req.budget_limit) if req.budget_limit else None,
                "created_at": req.created_at.isoformat(),
                "rider_id": req.rider_id
            }
            for req in requests
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{request_id}")
def get_request_details(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get request details with bill photos and attachments
    
    Authorization:
    - Customers can view their own requests
    - Riders can view assigned requests
    - Admins can view all requests
    """
    
    request = db.query(Request).filter(Request.request_id == request_id).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check authorization
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
    
    # Get customer info
    customer = db.query(User).filter(User.user_id == request.customer_id).first()
    
    # Get rider info if assigned
    rider_name = None
    rider_phone = None
    if request.rider_id:
        rider = db.query(Rider).filter(Rider.rider_id == request.rider_id).first()
        if rider and rider.user:
            rider_name = rider.user.full_name
            rider_phone = rider.user.phone_number
    
    return {
        "success": True,
        "message": "Request retrieved successfully",
        "data": {
            "request_id": request.request_id,
            "customer_id": request.customer_id,
            "customer_name": customer.full_name if customer else None,
            "customer_phone": customer.phone_number if customer else None,
            "rider_id": request.rider_id,
            "rider_name": rider_name,
            "rider_phone": rider_phone,
            "service_type": request.service_type,
            "items_description": request.items_description,
            "budget_limit": float(request.budget_limit) if request.budget_limit else None,
            "special_instructions": request.special_instructions,
            "status": request.status,
            "pickup_location": request.pickup_location,
            "delivery_address": request.delivery_address,
            "delivery_option": request.delivery_option,
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
    photo_url: str,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add bill photo to request
    
    Note: In production, handle file uploads via Cloudinary first,
    then pass the photo_url here
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
        photo_url=photo_url,
        file_name=file_name,
        file_size=file_size
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
    file_name: str,
    file_url: str,
    file_type: Optional[str] = None,
    file_size: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add file attachment to request
    
    Note: In production, handle file uploads via Cloudinary first,
    then pass the file_url here
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
        file_name=file_name,
        file_url=file_url,
        file_type=file_type,
        file_size=file_size
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
    
    return {
        "success": True,
        "message": "Request accepted successfully",
        "data": {
            "request_id": request.request_id,
            "status": request.status,
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
    
    Status flow:
    pending → assigned → in_progress → completed
    
    Any status → cancelled (except completed)
    """
    
    request = db.query(Request).filter(Request.request_id == request_id).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Authorization check
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
    
    # Status transition validation
    if request.status == RequestStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of completed request"
        )
    
    old_status = request.status
    request.status = new_status
    request.updated_at = datetime.utcnow()
    
    # Set completed_at if marking as completed
    if new_status == RequestStatus.completed:
        request.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(request)
    
    return {
        "success": True,
        "message": f"Request status updated from {old_status} to {new_status}",
        "data": {
            "request_id": request.request_id,
            "status": request.status,
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
            "status": request.status
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