from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional
from database import get_db
from models.user import User, UserType
from models.rider import Rider, RiderStatus
from models.bill_request import BillRequest, RequestStatus
from models.user_preference import UserPreference
from utils.dependencies import get_current_active_user, require_role
from utils.security import hash_password
from utils.cloudinary_manager import CloudinaryManager
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)
cloudinary_manager = CloudinaryManager()

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


# ============================================================================
# RIDER REGISTRATION WITH FILE UPLOAD
# ============================================================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_rider(
    # User registration fields
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
    address: str = Form(...),
    # Rider-specific fields
    vehicle_type: str = Form(...),
    vehicle_plate: str = Form(...),
    license_number: str = Form(...),
    id_number: str = Form(...),
    service_zones: str = Form(""),
    # Optional file upload
    id_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Register a new rider with optional ID document upload
    
    This endpoint:
    1. Creates a new user account with user_type='rider'
    2. Creates a rider profile linked to the user
    3. Uploads ID document to Cloudinary if provided
    4. Stores the Cloudinary URL in the rider profile
    
    Args:
        full_name: Rider's full name
        email: Valid email address
        phone_number: Valid phone number
        password: At least 8 characters
        address: Rider's address
        vehicle_type: Type of vehicle (e.g., 'motorcycle', 'tricycle', 'van')
        vehicle_plate: Vehicle plate number
        license_number: Driver's license number
        id_number: National ID or identification number
        service_zones: Comma-separated service zones (optional)
        id_file: ID document file to upload (optional)
    """
    
    try:
        # Validate phone number format
        phone_pattern = re.compile(r'^[0-9\s\-\+\(\)]{9,15}$')
        if not phone_pattern.match(phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
        
        # Validate password strength
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )
        
        # Validate full name length
        if len(full_name) < 2 or len(full_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name must be between 2 and 100 characters"
            )
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone number already exists
        existing_phone = db.query(User).filter(User.phone_number == phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Check if id_number already exists for a rider
        existing_id = db.query(Rider).filter(Rider.id_number == id_number).first()
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID number already registered"
            )
        
        # Create new user account
        new_user = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            password_hash=hash_password(password),
            user_type=UserType.rider,
            address=address,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Rider user account created: {new_user.email}")
        
        # Upload ID document to Cloudinary if provided
        id_document_url = None
        if id_file:
            try:
                # Set public_id to include rider info for organization
                public_id = f"riders/{new_user.user_id}/id_document"
                
                # Upload file to Cloudinary
                result = await cloudinary_manager.upload_file(
                    file=id_file,
                    public_id=public_id,
                    folder="pasugo/riders/id_documents"
                )
                
                id_document_url = result.get("secure_url")
                logger.info(f"ID document uploaded to Cloudinary for rider {new_user.user_id}")
            except Exception as e:
                logger.error(f"Failed to upload ID document to Cloudinary: {str(e)}")
                # Don't fail registration if upload fails, but log the error
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload ID document: {str(e)}"
                )
        
        # Create rider profile
        new_rider = Rider(
            user_id=new_user.user_id,
            id_number=id_number,
            vehicle_type=vehicle_type,
            vehicle_plate=vehicle_plate,
            license_number=license_number,
            id_document_url=id_document_url,
            availability_status=RiderStatus.offline
        )
        
        db.add(new_rider)
        
        # Create default user preferences
        user_pref = UserPreference(user_id=new_user.user_id)
        db.add(user_pref)
        
        db.commit()
        db.refresh(new_rider)
        
        logger.info(f"Rider profile created: {new_rider.rider_id}")
        
        return {
            "success": True,
            "message": "Rider registered successfully",
            "data": {
                "user_id": new_user.user_id,
                "rider_id": new_rider.rider_id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "phone_number": new_user.phone_number,
                "vehicle_type": new_rider.vehicle_type,
                "id_document_url": id_document_url,
                "user_type": "rider"
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error during rider registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register rider: {str(e)}"
        )


# ============================================================================
# EXISTING RIDER PROFILE ENDPOINTS
# ============================================================================

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