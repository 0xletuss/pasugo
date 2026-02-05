import random
import string
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OTPManager:
    """Manages OTP generation and validation for FastAPI"""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 5
    
    @staticmethod
    def generate_otp(length: int = OTP_LENGTH) -> str:
        """
        Generate a random OTP code
        
        Args:
            length: Length of OTP (default 6 digits)
        
        Returns:
            String containing random digits
        """
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def get_expiry_time(minutes: int = OTP_EXPIRY_MINUTES) -> datetime:
        """
        Calculate OTP expiry time
        
        Args:
            minutes: Minutes until expiry (default 10)
        
        Returns:
            DateTime object for expiry
        """
        return datetime.utcnow() + timedelta(minutes=minutes)
    
    @staticmethod
    def is_otp_expired(expires_at: datetime) -> bool:
        """
        Check if OTP has expired
        
        Args:
            expires_at: DateTime when OTP expires
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() > expires_at
    
    @staticmethod
    def can_attempt(attempts: int, max_attempts: int = MAX_ATTEMPTS) -> bool:
        """
        Check if user can make another OTP attempt
        
        Args:
            attempts: Current number of attempts
            max_attempts: Maximum allowed attempts
        
        Returns:
            True if user can attempt, False otherwise
        """
        return attempts < max_attempts
    
    @staticmethod
    def get_attempts_remaining(attempts: int, max_attempts: int = MAX_ATTEMPTS) -> int:
        """
        Get remaining attempts
        
        Args:
            attempts: Current number of attempts
            max_attempts: Maximum allowed attempts
        
        Returns:
            Number of remaining attempts
        """
        remaining = max_attempts - attempts
        return max(0, remaining)


# Create singleton instance
otp_manager = OTPManager()