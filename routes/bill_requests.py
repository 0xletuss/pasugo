from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from database import get_db
from models.user import User
from models.bill_request import BillRequest, RequestStatus, PaymentMethod
from utils.dependencies import get_current_active_user
from decimal import Decimal

router = APIRouter(prefix="/bill-requests", tags=["Bill Requests"])


# Schemas
class CreateBillRequestRequest(BaseModel):
    biller_name: str
    biller_category: str
    account_number: str
    bill_amount: float
    due_date: Optional[date] = None
    payment_method: PaymentMethod
    service_fee: float
    delivery_address: str
    contact_number: str
    preferred_time: Optional[datetime] = None
    special_instructions: Optional[str] = None


class BillRequestResponse(BaseModel):
    request_id: int
    customer_id: int
    biller_name: str
    biller_category: str
    account_number: str
    bill_amount: float
    request_status: str
    payment_method: str
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_bill_request(
    request: CreateBillRequestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new bill payment request"""
    
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create bill requests"
        )
    
    total_amount = Decimal(str(request.bill_amount)) + Decimal(str(request.service_fee))
    
    new_request = BillRequest(
        customer_id=current_user.user_id,
        biller_name=request.biller_name,
        biller_category=request.biller_category,
        account_number=request.account_number,
        bill_amount=Decimal(str(request.bill_amount)),
        due_date=request.due_date,
        payment_method=request.payment_method,
        service_fee=Decimal(str(request.service_fee)),
        total_amount=total_amount,
        delivery_address=request.delivery_address,
        contact_number=request.contact_number,
        preferred_time=request.preferred_time,
        special_instructions=request.special_instructions,
        request_status=RequestStatus.pending
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return {
        "success": True,
        "message": "Bill request created successfully",
        "data": {
            "request_id": new_request.request_id,
            "request_status": new_request.request_status,
            "total_amount": float(new_request.total_amount)
        }
    }


@router.get("/my-requests")
def get_my_requests(
    status: Optional[RequestStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's bill requests"""
    
    query = db.query(BillRequest).filter(BillRequest.customer_id == current_user.user_id)
    
    if status:
        query = query.filter(BillRequest.request_status == status)
    
    total = query.count()
    
    requests = query.order_by(BillRequest.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "success": True,
        "message": "Bill requests retrieved successfully",
        "data": [
            {
                "request_id": req.request_id,
                "biller_name": req.biller_name,
                "biller_category": req.biller_category,
                "bill_amount": float(req.bill_amount),
                "total_amount": float(req.total_amount),
                "request_status": req.request_status,
                "payment_method": req.payment_method,
                "created_at": req.created_at.isoformat(),
                "due_date": req.due_date.isoformat() if req.due_date else None
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
def get_bill_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get bill request details"""
    
    bill_request = db.query(BillRequest).filter(BillRequest.request_id == request_id).first()
    
    if not bill_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill request not found"
        )
    
    # Check authorization
    if current_user.user_type == "customer" and bill_request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )
    
    if current_user.user_type == "rider" and bill_request.rider_id != current_user.rider_profile.rider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )
    
    return {
        "success": True,
        "message": "Bill request retrieved successfully",
        "data": {
            "request_id": bill_request.request_id,
            "customer_id": bill_request.customer_id,
            "rider_id": bill_request.rider_id,
            "biller_name": bill_request.biller_name,
            "biller_category": bill_request.biller_category,
            "account_number": bill_request.account_number,
            "bill_amount": float(bill_request.bill_amount),
            "service_fee": float(bill_request.service_fee),
            "total_amount": float(bill_request.total_amount),
            "payment_method": bill_request.payment_method,
            "request_status": bill_request.request_status,
            "delivery_address": bill_request.delivery_address,
            "contact_number": bill_request.contact_number,
            "special_instructions": bill_request.special_instructions,
            "created_at": bill_request.created_at.isoformat(),
            "due_date": bill_request.due_date.isoformat() if bill_request.due_date else None
        }
    }


@router.patch("/{request_id}/cancel")
def cancel_bill_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a bill request"""
    
    bill_request = db.query(BillRequest).filter(BillRequest.request_id == request_id).first()
    
    if not bill_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill request not found"
        )
    
    if bill_request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this request"
        )
    
    if bill_request.request_status in [RequestStatus.completed, RequestStatus.cancelled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status: {bill_request.request_status}"
        )
    
    bill_request.request_status = RequestStatus.cancelled
    db.commit()
    
    return {
        "success": True,
        "message": "Bill request cancelled successfully"
    }