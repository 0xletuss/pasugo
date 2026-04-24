from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.rider import ApprovalStatus, Rider, RiderStatus
from models.user import User
from routes.admin import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Rider Approval"])


class RejectRiderRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=5, max_length=500)


# ═══════════════════════════════════════════════════════════════════════════════
#  RIDER APPROVAL MANAGEMENT (Admin Verification of Selfie & ID)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/riders/approval/pending")
def list_pending_riders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get riders pending approval (waiting for selfie + ID verification)"""
    
    q = db.query(Rider).options(joinedload(Rider.user)).filter(
        Rider.approval_status == ApprovalStatus.pending
    )
    
    total = q.count()
    riders = q.order_by(Rider.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for rider in riders:
        result.append({
            "rider_id": rider.rider_id,
            "user_id": rider.user_id,
            "full_name": rider.user.full_name if rider.user else None,
            "email": rider.user.email if rider.user else None,
            "phone": rider.user.phone_number if rider.user else None,
            "id_number": rider.id_number,
            "vehicle_type": rider.vehicle_type,
            "vehicle_plate": rider.vehicle_plate,
            "license_number": rider.license_number,
            "selfie_url": rider.selfie_url,
            "id_document_url": rider.id_document_url,
            "approval_status": rider.approval_status,
            "documents_ready": bool(rider.selfie_url and rider.id_document_url),
            "created_at": rider.created_at.isoformat() if rider.created_at else None,
        })
    
    return {
        "success": True,
        "message": f"Found {total} riders pending approval",
        "data": result,
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


@router.post("/riders/{rider_id}/approve")
def approve_rider(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve a rider's selfie and ID documents - allows them to accept deliveries"""
    
    try:
        rider = db.query(Rider).options(joinedload(Rider.user)).filter(Rider.rider_id == rider_id).first()
        
        if not rider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
        
        # Validate documents exist
        if not rider.selfie_url or not rider.id_document_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rider must upload both selfie and ID document before approval"
            )
        
        if rider.approval_status == ApprovalStatus.approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rider already approved"
            )
        
        # Update approval status
        rider.approval_status = ApprovalStatus.approved
        rider.approved_by = admin.user_id
        rider.approved_at = datetime.utcnow()
        rider.availability_status = RiderStatus.offline  # Set to offline (rider can change to available)
        
        db.commit()
        db.refresh(rider)
        
        logger.info(f"Admin {admin.email} approved rider {rider_id} ({rider.user.full_name if rider.user else ''})")
        
        return {
            "success": True,
            "message": f"Rider {rider.user.full_name if rider.user else f'#{rider_id}'} has been approved!",
            "data": {
                "rider_id": rider.rider_id,
                "full_name": rider.user.full_name if rider.user else None,
                "approval_status": rider.approval_status,
                "approved_at": rider.approved_at.isoformat(),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving rider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve rider"
        )


@router.post("/riders/{rider_id}/reject")
def reject_rider(
    rider_id: int,
    request: RejectRiderRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reject a rider's application with a reason"""
    
    try:
        rider = db.query(Rider).options(joinedload(Rider.user)).filter(Rider.rider_id == rider_id).first()
        
        if not rider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
        
        if rider.approval_status == ApprovalStatus.approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an already-approved rider"
            )
        
        # Update approval status
        rider.approval_status = ApprovalStatus.rejected
        rider.approved_by = admin.user_id
        rider.approved_at = datetime.utcnow()
        rider.rejection_reason = request.rejection_reason
        
        # Deactivate rider account
        if rider.user:
            rider.user.is_active = False
        
        db.commit()
        db.refresh(rider)
        
        logger.info(f"Admin {admin.email} rejected rider {rider_id} - Reason: {request.rejection_reason}")
        
        return {
            "success": True,
            "message": f"Rider application rejected",
            "data": {
                "rider_id": rider.rider_id,
                "full_name": rider.user.full_name if rider.user else None,
                "approval_status": rider.approval_status,
                "rejection_reason": rider.rejection_reason,
                "rejected_at": rider.approved_at.isoformat(),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting rider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject rider"
        )


@router.get("/riders/{rider_id}/approval-details")
def get_rider_approval_details(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get detailed approval information for a rider (including document URLs)"""
    
    try:
        rider = db.query(Rider).options(joinedload(Rider.user)).filter(Rider.rider_id == rider_id).first()
        
        if not rider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
        
        approved_by_user = None
        if rider.approved_by:
            approved_by_user = db.query(User).filter(User.user_id == rider.approved_by).first()
        
        return {
            "success": True,
            "data": {
                "rider_id": rider.rider_id,
                "user_id": rider.user_id,
                "full_name": rider.user.full_name if rider.user else None,
                "email": rider.user.email if rider.user else None,
                "phone": rider.user.phone_number if rider.user else None,
                "address": rider.user.address if rider.user else None,
                "id_number": rider.id_number,
                "vehicle_type": rider.vehicle_type,
                "vehicle_plate": rider.vehicle_plate,
                "license_number": rider.license_number,
                "approval_status": rider.approval_status,
                "selfie_url": rider.selfie_url,
                "id_document_url": rider.id_document_url,
                "rejection_reason": rider.rejection_reason,
                "approved_by": {
                    "user_id": approved_by_user.user_id,
                    "name": approved_by_user.full_name,
                } if approved_by_user else None,
                "approved_at": rider.approved_at.isoformat() if rider.approved_at else None,
                "created_at": rider.created_at.isoformat() if rider.created_at else None,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rider approval details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rider approval details"
        )
