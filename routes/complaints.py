from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from models.complaint import Complaint, ComplaintReply, ComplaintStatus
from utils.dependencies import get_current_active_user

router = APIRouter(prefix="/complaints", tags=["Complaints"])


# Schemas
class CreateComplaintRequest(BaseModel):
    request_id: int
    complaint_type: str
    title: str
    description: str


class AddReplyRequest(BaseModel):
    reply_message: str


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_complaint(
    request: CreateComplaintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new complaint"""
    
    new_complaint = Complaint(
        request_id=request.request_id,
        customer_id=current_user.user_id,
        complaint_type=request.complaint_type,
        title=request.title,
        description=request.description,
        status=ComplaintStatus.open
    )
    
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    
    return {
        "success": True,
        "message": "Complaint created successfully",
        "data": {
            "complaint_id": new_complaint.complaint_id,
            "status": new_complaint.status
        }
    }


@router.get("/my-complaints")
def get_my_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's complaints with pagination"""
    
    query = db.query(Complaint) \
        .filter(Complaint.customer_id == current_user.user_id)
    
    total = query.count()
    
    complaints = query.order_by(Complaint.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "success": True,
        "message": "Complaints retrieved successfully",
        "data": [
            {
                "complaint_id": c.complaint_id,
                "request_id": c.request_id,
                "complaint_type": c.complaint_type,
                "title": c.title,
                "status": c.status,
                "created_at": c.created_at.isoformat()
            }
            for c in complaints
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{complaint_id}")
def get_complaint_details(
    complaint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complaint details with replies"""
    
    complaint = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    if complaint.customer_id != current_user.user_id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this complaint"
        )
    
    return {
        "success": True,
        "message": "Complaint details retrieved successfully",
        "data": {
            "complaint_id": complaint.complaint_id,
            "request_id": complaint.request_id,
            "complaint_type": complaint.complaint_type,
            "title": complaint.title,
            "description": complaint.description,
            "status": complaint.status,
            "created_at": complaint.created_at.isoformat(),
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "replies": [
                {
                    "reply_id": r.reply_id,
                    "admin_id": r.admin_id,
                    "reply_message": r.reply_message,
                    "created_at": r.created_at.isoformat()
                }
                for r in complaint.replies
            ]
        }
    }


@router.post("/{complaint_id}/reply")
def add_reply(
    complaint_id: int,
    request: AddReplyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a reply to complaint (admin only)"""
    
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reply to complaints"
        )
    
    complaint = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    new_reply = ComplaintReply(
        complaint_id=complaint_id,
        admin_id=current_user.user_id,
        reply_message=request.reply_message
    )
    
    complaint.status = ComplaintStatus.in_progress
    
    db.add(new_reply)
    db.commit()
    
    return {
        "success": True,
        "message": "Reply added successfully"
    }