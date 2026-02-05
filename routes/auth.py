from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from database import get_db
from models.user import User, UserType
from models.user_preference import UserPreference
from utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from datetime import timedelta
import logging

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

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password length (bcrypt limit is 72 bytes)"""
        if isinstance(v, str):
            password_bytes = v.encode('utf-8')
        else:
            password_bytes = v
        
        if len(password_bytes) > 72:
            raise ValueError('Password must be no longer than 72 bytes when encoded in UTF-8')
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    
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
            address=request.address
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create default user preferences
        user_pref = UserPreference(user_id=new_user.user_id)
        db.add(user_pref)
        db.commit()
        
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "user_id": new_user.user_id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "user_type": new_user.user_type
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.user_id, "email": user.email, "user_type": user.user_type}
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": user.user_id}
        )
        
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
                    "user_type": user.user_type,
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
            detail=f"Login failed: {str(e)}"
        )


@router.post("/logout")
def logout():
    """Logout user (token should be blacklisted on client side)"""
    return {
        "success": True,
        "message": "Logged out successfully"
    }