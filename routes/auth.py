from fastapi import APIRouter, Depends, HTTPException, status, Header
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
from typing import Optional
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# SCHEMAS
# ============================================================================

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
    remember_me: bool = True  # Default to persistent login


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


# ============================================================================
# DEPENDENCY TO GET CURRENT USER
# ============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and verify user from Authorization header"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# ROUTES
# ============================================================================

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
    - **remember_me**: Keep user logged in (default: true)
    
    Returns access and refresh tokens for subsequent requests.
    Access token expires in 15 minutes.
    Refresh token expires in 30 days (if remember_me=true) or 1 day (if remember_me=false).
    """
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
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
        
        # Create access token (short-lived: 15 minutes)
        access_token = create_access_token(
            data={
                "sub": str(user.user_id), 
                "email": user.email, 
                "user_type": str(user.user_type)
            }
        )
        
        # Create refresh token (long-lived: 30 days for persistent login, 1 day otherwise)
        refresh_expiry = timedelta(days=30) if request.remember_me else timedelta(days=1)
        refresh_token = create_refresh_token(
            data={"sub": str(user.user_id)},
            expires_delta=refresh_expiry
        )
        
        logger.info(f"User logged in: {user.email} (remember_me={request.remember_me})")
        
        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "remember_me": request.remember_me,
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
    
    Returns new access token and new refresh token (token rotation for security).
    Call this endpoint when access token expires to get a new one without re-login.
    """
    
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)
        
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user from database
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        new_access_token = create_access_token(
            data={
                "sub": str(user.user_id), 
                "email": user.email, 
                "user_type": str(user.user_type)
            }
        )
        
        # Rotate refresh token for better security (issue new one)
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.user_id)},
            expires_delta=timedelta(days=30)
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,  # Return new refresh token
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


@router.post("/validate-token")
def validate_token_endpoint(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Validate if the current token is still valid
    
    Use this endpoint on app startup to check if user is still authenticated.
    Returns user data if token is valid.
    """
    
    if not authorization:
        return {
            "success": False,
            "valid": False,
            "message": "No token provided"
        }
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return {
                "success": False,
                "valid": False,
                "message": "Invalid authentication scheme"
            }
        
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user or not user.is_active:
            return {
                "success": False,
                "valid": False,
                "message": "User not found or inactive"
            }
        
        return {
            "success": True,
            "valid": True,
            "message": "Token is valid",
            "data": {
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
        
    except Exception as e:
        logger.debug(f"Token validation failed: {str(e)}")
        return {
            "success": False,
            "valid": False,
            "message": "Invalid or expired token"
        }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password
    
    - **old_password**: Current password
    - **new_password**: New password (must be different from old)
    
    Requires authentication token in Authorization header.
    """
    
    try:
        # Verify old password
        if not verify_password(request.old_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Check if new password is different
        if request.old_password == request.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from old password"
            )
        
        # Update password
        current_user.password_hash = hash_password(request.new_password)
        db.commit()
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {
            "success": True,
            "message": "Password changed successfully. Please log in again with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout user
    
    Note: Delete the stored tokens on the client side.
    The refresh token will become invalid after its expiration.
    For enhanced security, you could implement token blacklisting.
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return {
        "success": True,
        "message": "Logged out successfully. Please delete stored tokens on client."
    }


@router.get("/me")
def get_current_user_details(current_user: User = Depends(get_current_user)):
    """Get current user details
    
    Requires authentication token in Authorization header.
    Format: Authorization: Bearer <token>
    """
    
    return {
        "success": True,
        "data": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "user_type": str(current_user.user_type) if hasattr(current_user.user_type, 'value') else current_user.user_type,
            "phone_number": current_user.phone_number,
            "address": current_user.address,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user.created_at, 'isoformat') else str(current_user.created_at)
        }
    }