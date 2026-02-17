from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
from models.user import User
from utils.dependencies import get_current_active_user

router = APIRouter(prefix="/users", tags=["Users"])


# Schemas
class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone_number: str
    user_type: str
    address: str = None
    profile_photo_url: str = None
    is_active: bool
    created_at: str = None

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    full_name: str = None
    phone_number: str = None
    address: str = None
    profile_photo_url: str = None


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current logged in user information"""
    return current_user


@router.put("/me")
def update_current_user(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    
    if request.full_name:
        current_user.full_name = request.full_name
    
    if request.phone_number:
        # Check if phone number is already used by another user
        existing = db.query(User).filter(
            User.phone_number == request.phone_number,
            User.user_id != current_user.user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use"
            )
        current_user.phone_number = request.phone_number
    
    if request.address:
        current_user.address = request.address
    
    if request.profile_photo_url is not None:
        current_user.profile_photo_url = request.profile_photo_url
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "success": True,
        "message": "User updated successfully",
        "data": {
            "user_id": current_user.user_id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "address": current_user.address,
            "profile_photo_url": current_user.profile_photo_url
        }
    }


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user by ID (admin only or own profile)"""
    
    if current_user.user_type != "admin" and current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user