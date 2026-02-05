"""
File Upload Routes
Handles all media uploads to Cloudinary
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.rider import Rider
from models.bill_request import BillRequest
from models.complaint import Complaint
from utils.dependencies import get_current_active_user
from utils.cloudinary_manager import CloudinaryManager
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["File Uploads"])


@router.post("/rider-id")
async def upload_rider_id(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload rider ID document to Cloudinary
    
    - **file**: ID document file (PDF, image, etc.)
    - **Returns**: Cloudinary URL of the uploaded document
    
    Requires authentication and rider account type.
    """
    try:
        # Check if user is a rider
        if current_user.user_type != "rider":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders can upload ID documents"
            )
        
        # Get rider profile
        rider = db.query(Rider).filter(Rider.user_id == current_user.user_id).first()
        
        if not rider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider profile not found"
            )
        
        # Upload to Cloudinary
        result = await CloudinaryManager.upload_file(
            file,
            folder=f"riders/id_documents",
            public_id=f"rider_{rider.rider_id}",
            resource_type="auto"
        )
        
        # Update rider profile with ID document URL
        rider.id_document_url = result["url"]
        db.commit()
        db.refresh(rider)
        
        logger.info(f"Rider ID uploaded for rider {rider.rider_id}")
        
        return {
            "success": True,
            "message": "ID document uploaded successfully",
            "data": {
                "url": result["url"],
                "public_id": result["public_id"],
                "format": result["format"],
                "size": result["size"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rider ID upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload rider ID: {str(e)}"
        )


@router.post("/bill-photo")
async def upload_bill_photo(
    request_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload bill photo to Cloudinary
    
    - **request_id**: Bill request ID
    - **file**: Bill photo file (JPEG, PNG, etc.)
    - **Returns**: Cloudinary URL of the uploaded photo
    
    Requires authentication. Only the bill owner can upload bill photo.
    """
    try:
        # Get bill request
        bill_request = db.query(BillRequest).filter(
            BillRequest.request_id == request_id
        ).first()
        
        if not bill_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill request not found"
            )
        
        # Check authorization (customer or admin)
        if bill_request.customer_id != current_user.user_id and current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload bill photo for this request"
            )
        
        # Validate file is an image
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bill photo must be an image file"
            )
        
        # Upload to Cloudinary
        result = await CloudinaryManager.upload_file(
            file,
            folder="bills/photos",
            public_id=f"bill_{request_id}",
            resource_type="image"
        )
        
        # Update bill request with photo URL
        bill_request.bill_photo_url = result["url"]
        db.commit()
        db.refresh(bill_request)
        
        logger.info(f"Bill photo uploaded for request {request_id}")
        
        return {
            "success": True,
            "message": "Bill photo uploaded successfully",
            "data": {
                "url": result["url"],
                "public_id": result["public_id"],
                "width": result.get("width"),
                "height": result.get("height")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bill photo upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload bill photo: {str(e)}"
        )


@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload user profile photo to Cloudinary
    
    - **file**: Profile photo file (JPEG, PNG, etc.)
    - **Returns**: Cloudinary URL of the uploaded photo
    
    Requires authentication. Updates current user's profile photo.
    """
    try:
        # Validate file is an image
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile photo must be an image file"
            )
        
        # Upload to Cloudinary
        result = await CloudinaryManager.upload_file(
            file,
            folder="users/profile_photos",
            public_id=f"user_{current_user.user_id}",
            resource_type="image"
        )
        
        # Update user profile with photo URL
        current_user.profile_photo_url = result["url"]
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Profile photo uploaded for user {current_user.user_id}")
        
        return {
            "success": True,
            "message": "Profile photo uploaded successfully",
            "data": {
                "url": result["url"],
                "public_id": result["public_id"],
                "width": result.get("width"),
                "height": result.get("height"),
                "thumbnail_url": CloudinaryManager.generate_thumbnail(result["public_id"], 150, 150)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile photo upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile photo: {str(e)}"
        )


@router.post("/complaint-attachment")
async def upload_complaint_attachment(
    complaint_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload complaint attachment to Cloudinary
    
    - **complaint_id**: Complaint ID
    - **file**: Attachment file (image, PDF, etc.)
    - **Returns**: Cloudinary URL of the uploaded attachment
    
    Requires authentication. Only the complaint creator or admin can upload.
    """
    try:
        # Get complaint
        complaint = db.query(Complaint).filter(
            Complaint.complaint_id == complaint_id
        ).first()
        
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found"
            )
        
        # Check authorization
        if complaint.customer_id != current_user.user_id and current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload attachment for this complaint"
            )
        
        # Upload to Cloudinary
        result = await CloudinaryManager.upload_file(
            file,
            folder="complaints/attachments",
            public_id=f"complaint_{complaint_id}_{file.filename.split('.')[0]}",
            resource_type="auto"
        )
        
        logger.info(f"Complaint attachment uploaded for complaint {complaint_id}")
        
        return {
            "success": True,
            "message": "Complaint attachment uploaded successfully",
            "data": {
                "url": result["url"],
                "public_id": result["public_id"],
                "format": result.get("format"),
                "size": result.get("size")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complaint attachment upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload complaint attachment: {str(e)}"
        )


@router.delete("/remove/{resource_type}/{public_id}")
async def delete_file(
    resource_type: str,
    public_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete uploaded file from Cloudinary
    
    - **resource_type**: Type of resource (image, video, raw)
    - **public_id**: Public ID of the file to delete
    
    Note: Only admins or file owners can delete files.
    """
    try:
        # Only admins can delete files for now (add owner check if needed)
        if current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete files"
            )
        
        # Delete from Cloudinary
        success = CloudinaryManager.delete_file(public_id, resource_type)
        
        if success:
            logger.info(f"File deleted: {public_id}")
            return {
                "success": True,
                "message": "File deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file from Cloudinary"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/health")
async def check_cloudinary_health():
    """Check if Cloudinary is properly configured and accessible
    
    - **Returns**: Cloudinary health status
    
    Useful for debugging upload issues.
    """
    try:
        is_healthy = CloudinaryManager.health_check()
        
        if is_healthy:
            return {
                "success": True,
                "status": "healthy",
                "message": "Cloudinary is connected and working properly"
            }
        else:
            return {
                "success": False,
                "status": "unhealthy",
                "message": "Cloudinary connection failed"
            }
            
    except Exception as e:
        logger.error(f"Cloudinary health check error: {str(e)}")
        return {
            "success": False,
            "status": "error",
            "message": f"Health check error: {str(e)}"
        }
