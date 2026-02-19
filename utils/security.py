from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from config import settings
from fastapi import HTTPException, status


def hash_password(password: str) -> str:
    """Hash a password using bcrypt
    
    Bcrypt has a maximum password length of 72 bytes.
    Passwords longer than 72 bytes are truncated.
    """
    # Convert to bytes and truncate to 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash
    
    Bcrypt has a maximum password length of 72 bytes.
    Passwords longer than 72 bytes are truncated for verification.
    """
    # Convert password to bytes and truncate to 72 bytes
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Convert hash to bytes if it's a string
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    # Verify
    return bcrypt.checkpw(password_bytes, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token
    
    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token
    
    Args:
        data: Dictionary containing user data to encode (usually just user_id)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload dictionary
        
    Raises:
        HTTPException: If token is invalid or expired
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
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload dictionary or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure random OTP code
    
    Args:
        length: Length of OTP (default: 6)
        
    Returns:
        Random numeric OTP string
    """
    import secrets
    # Generate a secure random number with the specified number of digits
    max_val = 10 ** length
    otp_num = secrets.randbelow(max_val)
    return str(otp_num).zfill(length)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength
    
    Args:
        password: Password string to validate
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    
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