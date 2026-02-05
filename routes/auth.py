from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from database import get_db
from models.user import User, UserType
from models.user_preference import UserPreference
from utils.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_token,
    validate_password_strength
)
from datetime import timedelta, datetime
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Schemas
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    password: str
    user_type: UserType
    address: str = None

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        """Validate full name"""
        if not v or len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Full name cannot exceed 100 characters')
        return v.strip()

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Allow common international formats
        phone_pattern = r'^\+?1?\d{9,15}$'
        if not re.match(phone_pattern, v.replace(' ', '').replace('-', '')):
            raise ValueError('Invalid phone number format')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password"""
        if isinstance(v, str):
            password_bytes = v.encode('utf-8')
        else:
            password_bytes = v
        
        if len(password_bytes) > 72:
            raise ValueError('Password must be no longer than 72 bytes when encoded in UTF-8')
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password"""
        if isinstance(v, str):
            password_bytes = v.encode('utf-8')
        else:
            password_bytes = v
        
        if len(password_bytes) > 72:
            raise ValueError('Password must be no longer than 72 bytes when encoded in UTF-8')
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        return v


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# Routes
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user
    
    - **full_name**: User's full name (2-100 characters)
    - **email**: Valid email address
    - **phone_number**: Valid phone number
    - **password**: At least 8 characters, max 72 bytes
    - **user_type**: Either 'customer' or 'vendor'
    - **address**: Optional address
    """
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check phone number
        existing_phone = db.query(User).filter(User.phone_number == request.phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Create new user
        new_user = User(
            full_name=request.full_name,
            email=request.email,
            phone_number=request.phone_number,
            password_hash=hash_password(request.password),
            user_type=request.user_type,
            address=request.address,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create default user preferences
        user_pref = UserPreference(user_id=new_user.user_id)
        db.add(user_pref)
        db.commit()
        
        logger.info(f"User registered: {new_user.email}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "user_id": new_user.user_id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "user_type": new_user.user_type.value if hasattr(new_user.user_type, 'value') else new_user.user_type
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT tokens
    
    - **email**: User's email
    - **password**: User's password
    
    Returns access and refresh tokens for subsequent requests
    """
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Generic message for security
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"Failed login attempt for: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive. Please contact support."
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email, "user_type": str(user.user_type)}
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(user.user_id)}
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "user_type": str(user.user_type) if hasattr(user.user_type, 'value') else user.user_type,
                    "phone_number": user.phone_number,
                    "address": user.address
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/refresh")
def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Get a new access token using refresh token
    
    - **refresh_token**: Valid refresh token from login
    
    Returns new access token
    """
    
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)
        
        user_id = payload.get("sub")
        
        # Get user from database
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        new_access_token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email, "user_type": str(user.user_type)}
        )
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "data": {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    """Change user password
    
    - **old_password**: Current password
    - **new_password**: New password (must be different from old)
    
    Requires authentication token
    """
    
    try:
        # This would require getting current_user from token
        # For now, placeholder implementation
        # In production, you'd have a dependency to get current user from token
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/logout")
def logout():
    """Logout user
    
    Note: On the client side, delete the stored tokens.
    On the server side, you may want to implement token blacklisting
    for additional security (optional).
    """
    return {
        "success": True,
        "message": "Logged out successfully. Please delete stored tokens on client."
    }


@router.get("/me")
def get_current_user(token: str = None, db: Session = Depends(get_db)):
    """Get current user details
    
    Requires authentication token in Authorization header
    Format: Authorization: Bearer <token>
    """
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "success": True,
            "data": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": str(user.user_type) if hasattr(user.user_type, 'value') else user.user_type,
                "phone_number": user.phone_number,
                "address": user.address,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if hasattr(user.created_at, 'isoformat') else str(user.created_at)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )