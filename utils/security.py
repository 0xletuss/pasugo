from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
from fastapi import HTTPException, status

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt
    
    Bcrypt has a maximum password length of 72 bytes.
    Passwords longer than 72 bytes are truncated.
    """
    # Truncate password to 72 bytes (bcrypt limit)
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    if len(password) > 72:
        password = password[:72]
    
    # Convert back to string if needed
    if isinstance(password, bytes):
        password = password.decode('utf-8')
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash
    
    Bcrypt has a maximum password length of 72 bytes.
    Passwords longer than 72 bytes are truncated for verification.
    """
    # Truncate password to 72 bytes (bcrypt limit) - must match hashing behavior
    if isinstance(plain_password, str):
        password_bytes = plain_password.encode('utf-8')
    else:
        password_bytes = plain_password
    
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Convert back to string if needed
    if isinstance(password_bytes, bytes):
        plain_password = password_bytes.decode('utf-8')
    else:
        plain_password = password_bytes
    
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token
    
    Raises HTTPException with 401 status if token is invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token_silent(token: str) -> Optional[dict]:
    """Verify and decode a JWT token (returns None instead of raising exception)
    
    Use this when you don't want to raise an exception.
    Returns None if token is invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp(length: int = 6) -> str:
    """Generate a random OTP code"""
    import random
    import string
    return ''.join(random.choices(string.digits, k=length))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength
    
    Returns:
        (is_valid: bool, message: str)
    
    Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*()...)"
    
    return True, "Password is strong"