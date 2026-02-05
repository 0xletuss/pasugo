from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from models.rider import Rider, RiderStatus
from models.bill_request import BillRequest, RequestStatus
from utils.dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/riders", tags=["Riders"])


# Schemas
class CreateRiderProfileRequest(BaseModel):
    id_number: str  # National ID or document number
    vehicle_type: str
    vehicle_plate: str
    license_number: str


class UpdateRiderLocationRequest(BaseModel):
    latitude: float
    longitude: float


class UpdateRiderStatusRequest(BaseModel):
    status: RiderStatus


@router.post("/profile", status_code=status.HTTP_201_CREATED)
def create_rider_profile(
    request: CreateRiderProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create rider profile for user"""
    
    if current_user.user_type != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only rider accounts can create rider profile"
        )
    
    # Check if rider profile already exists
    existing = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rider profile already exists"
        )
    
    new_rider = Rider(
        user_id=current_user.user_id,
        id_number=request.id_number,
        vehicle_type=request.vehicle_type,
        license_plate=request.vehicle_plate,
        license_number=request.license_number,
        availability_status=RiderStatus.offline
    )
    
    db.add(new_rider)
    db.commit()
    db.refresh(new_rider)
    
    return {
        "success": True,
        "message": "Rider profile created successfully",
        "data": {
            "rider_id": new_rider.rider_id,
            "vehicle_type": new_rider.vehicle_type,
            "status": new_rider.availability_status
        }
    }


@router.get("/profile")
def get_rider_profile(
    current_user: User = Depends(require_role(["rider"])),
    db: Session = Depends(get_db)
):
    """Get current rider's profile"""
    
    rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider profile not found"
        )
    
    return {
        "success": True,
        "message": "Rider profile retrieved successfully",
        "data": {
            "rider_id": rider.rider_id,
            "vehicle_type": rider.vehicle_type,
            "vehicle_plate": rider.vehicle_plate,
            "license_number": rider.license_number,
            "status": rider.availability_status,
            "rating": float(rider.rating) if rider.rating else 0,
            "total_deliveries": rider.total_deliveries,
            "is_verified": rider.is_verified,
            "current_location": {
                "lat": rider.current_location_lat,
                "lng": rider.current_location_lng
            } if rider.current_location_lat else None
        }
    }


@router.patch("/location")
def update_rider_location(
    request: UpdateRiderLocationRequest,
    current_user: User = Depends(require_role(["rider"])),
    db: Session = Depends(get_db)
):
    """Update rider's current location"""
    
    rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider profile not found"
        )
    
    rider.current_location_lat = request.latitude
    rider.current_location_lng = request.longitude
    
    db.commit()
    
    return {
        "success": True,
        "message": "Location updated successfully"
    }


@router.patch("/status")
def update_rider_status(
    request: UpdateRiderStatusRequest,
    current_user: User = Depends(require_role(["rider"])),
    db: Session = Depends(get_db)
):
    """Update rider's availability status"""
    
    rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider profile not found"
        )
    
    rider.availability_status = request.status
    db.commit()
    
    return {
        "success": True,
        "message": f"Status updated to {request.status}"
    }


@router.get("/available-requests")
def get_available_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(["rider"])),
    db: Session = Depends(get_db)
):
    """Get available bill requests for riders"""
    
    query = db.query(BillRequest).filter(
        BillRequest.request_status == RequestStatus.pending,
        BillRequest.rider_id == None
    )
    
    total = query.count()
    
    requests = query.order_by(BillRequest.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "success": True,
        "message": "Available requests retrieved successfully",
        "data": [
            {
                "request_id": req.request_id,
                "biller_name": req.biller_name,
                "biller_category": req.biller_category,
                "total_amount": float(req.total_amount),
                "delivery_address": req.delivery_address,
                "created_at": req.created_at.isoformat()
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


@router.post("/accept-request/{request_id}")
def accept_request(
    request_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: Session = Depends(get_db)
):
    """Accept a bill request"""
    
    rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
    
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider profile not found"
        )
    
    bill_request = db.query(BillRequest).filter(BillRequest.request_id == request_id).first()
    
    if not bill_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill request not found"
        )
    
    if bill_request.request_status != RequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request is not available"
        )
    
    if bill_request.rider_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request already assigned to another rider"
        )
    
    bill_request.rider_id = rider.rider_id
    bill_request.request_status = RequestStatus.assigned
    rider.availability_status = RiderStatus.busy
    
    db.commit()
    
    return {
        "success": True,
        "message": "Request accepted successfully"
    }