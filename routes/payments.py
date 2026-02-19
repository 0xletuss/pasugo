from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models.user import User
from models.payment import Payment, PaymentStatus, PaymentMethod
from models.bill_request import BillRequest
from utils.dependencies import get_current_active_user
from decimal import Decimal

router = APIRouter(prefix="/payments", tags=["Payments"])


# Schemas
class CreatePaymentRequest(BaseModel):
    request_id: int
    payment_method: PaymentMethod
    transaction_reference: str = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_payment(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a payment for a bill request"""
    
    bill_request = db.query(BillRequest).filter(
        BillRequest.request_id == request.request_id
    ).first()
    
    if not bill_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill request not found"
        )
    
    if bill_request.customer_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create payment for this request"
        )
    
    # Check if payment already exists
    existing_payment = db.query(Payment).filter(
        Payment.request_id == request.request_id
    ).first()
    
    if existing_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already exists for this request"
        )
    
    new_payment = Payment(
        request_id=request.request_id,
        customer_id=current_user.user_id,
        payment_method=request.payment_method,
        amount=bill_request.total_amount,
        payment_status=PaymentStatus.pending,
        transaction_reference=request.transaction_reference
    )
    
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    
    return {
        "success": True,
        "message": "Payment created successfully",
        "data": {
            "payment_id": new_payment.payment_id,
            "amount": float(new_payment.amount),
            "payment_status": new_payment.payment_status
        }
    }


@router.get("/my-payments")
def get_my_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's payments with pagination"""
    
    query = db.query(Payment) \
        .filter(Payment.customer_id == current_user.user_id)
    
    total = query.count()
    
    payments = query.order_by(Payment.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "success": True,
        "message": "Payments retrieved successfully",
        "data": [
            {
                "payment_id": p.payment_id,
                "request_id": p.request_id,
                "amount": float(p.amount),
                "payment_method": p.payment_method,
                "payment_status": p.payment_status,
                "transaction_reference": p.transaction_reference,
                "created_at": p.created_at.isoformat()
            }
            for p in payments
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{payment_id}")
def get_payment_details(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get payment details"""
    
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.customer_id != current_user.user_id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return {
        "success": True,
        "message": "Payment details retrieved successfully",
        "data": {
            "payment_id": payment.payment_id,
            "request_id": payment.request_id,
            "customer_id": payment.customer_id,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "payment_status": payment.payment_status,
            "transaction_reference": payment.transaction_reference,
            "created_at": payment.created_at.isoformat(),
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None
        }
    }