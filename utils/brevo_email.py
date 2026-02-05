import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BrevoEmailSender:
    """Handles all Brevo email sending operations for FastAPI"""
    
    def __init__(self):
        """Initialize Brevo API configuration"""
        try:
            from sib_api_v3_sdk import ApiClient, Configuration
            from sib_api_v3_sdk.apis.transactional_emails_api import TransactionalEmailsApi
            from sib_api_v3_sdk.models.send_smtp_email import SendSmtpEmail
        except ImportError as e:
            logger.error(f"Failed to import sib_api_v3_sdk: {e}")
            raise
        
        api_key = os.getenv("BREVO_API_KEY")
        
        if not api_key:
            raise ValueError("BREVO_API_KEY not found in environment variables")
        
        # Configure Brevo API client
        configuration = Configuration()
        configuration.api_key["api-key"] = api_key
        
        self.api_client = ApiClient(configuration)
        self.api_instance = TransactionalEmailsApi(self.api_client)
        self.SendSmtpEmail = SendSmtpEmail
        
        self.sender_email = os.getenv("SENDER_EMAIL", "bayadpasugo@gmail.com")
        self.sender_name = os.getenv("SENDER_NAME", "Pasugo App")
    
    def send_registration_otp(self, recipient_email: str, otp_code: str) -> Dict[str, Any]:
        """Send OTP email for registration"""
        return self._send_otp_email(
            recipient_email=recipient_email,
            otp_code=otp_code,
            subject="Your OTP Code for Registration",
            email_type="registration"
        )
    
    def send_login_otp(self, recipient_email: str, otp_code: str) -> Dict[str, Any]:
        """Send OTP email for login"""
        return self._send_otp_email(
            recipient_email=recipient_email,
            otp_code=otp_code,
            subject="Your OTP Code for Login",
            email_type="login"
        )
    
    def send_password_reset_otp(self, recipient_email: str, otp_code: str) -> Dict[str, Any]:
        """Send OTP email for password reset"""
        return self._send_otp_email(
            recipient_email=recipient_email,
            otp_code=otp_code,
            subject="Reset Your Password - OTP Code",
            email_type="password_reset"
        )
    
    def send_phone_verification_otp(self, recipient_email: str, otp_code: str, phone_number: str) -> Dict[str, Any]:
        """Send OTP email for phone verification"""
        return self._send_otp_email(
            recipient_email=recipient_email,
            otp_code=otp_code,
            subject="Verify Your Phone Number - OTP Code",
            email_type="phone_verification",
            phone_number=phone_number
        )
    
    def _send_otp_email(
        self,
        recipient_email: str,
        otp_code: str,
        subject: str,
        email_type: str,
        phone_number: str = None
    ) -> Dict[str, Any]:
        """Internal method to send OTP email"""
        
        try:
            # Create HTML content based on email type
            if email_type == "registration":
                html_content = self._get_registration_html(otp_code)
            elif email_type == "login":
                html_content = self._get_login_html(otp_code)
            elif email_type == "phone_verification":
                html_content = self._get_phone_verification_html(otp_code, phone_number)
            else:  # password_reset
                html_content = self._get_password_reset_html(otp_code)
            
            # Create email object for Brevo SDK
            send_smtp_email = self.SendSmtpEmail(
                to=[{"email": recipient_email}],
                sender={"name": self.sender_name, "email": self.sender_email},
                subject=subject,
                html_content=html_content,
                reply_to={"email": self.sender_email}
            )
            
            # Send email via Brevo API
            response = self.api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"✓ OTP email sent successfully to {recipient_email} (Type: {email_type})")
            
            return {
                "success": True,
                "message": "OTP sent to your email",
                "message_id": getattr(response, 'message_id', None)
            }
        
        except Exception as e:
            logger.error(f"✗ Error sending OTP email to {recipient_email}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "Failed to send OTP",
                "error": str(e)
            }
    
    def _get_registration_html(self, otp_code: str) -> str:
        """HTML template for registration OTP"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Welcome to Pasugo!</h2>
                    <p style="color: #666; font-size: 16px;">Your One-Time Password (OTP) for registration is:</p>
                    
                    <div style="background-color: #007bff; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 14px; margin: 0 0 10px 0; color: #e0e0e0;">OTP Code</p>
                        <h1 style="font-size: 48px; letter-spacing: 5px; margin: 0; font-weight: bold;">{otp_code}</h1>
                    </div>
                    
                    <p style="color: #999; font-size: 14px; text-align: center;">This code is valid for 10 minutes</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 14px;">If you didn't request this registration, please ignore this email and do not share this code with anyone.</p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">
                        Best regards,<br>
                        <strong>Pasugo Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _get_login_html(self, otp_code: str) -> str:
        """HTML template for login OTP"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Login Verification</h2>
                    <p style="color: #666; font-size: 16px;">Your One-Time Password (OTP) for login is:</p>
                    
                    <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 14px; margin: 0 0 10px 0; color: #e0e0e0;">OTP Code</p>
                        <h1 style="font-size: 48px; letter-spacing: 5px; margin: 0; font-weight: bold;">{otp_code}</h1>
                    </div>
                    
                    <p style="color: #999; font-size: 14px; text-align: center;">This code is valid for 10 minutes</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 14px;">If you didn't request this login, please ignore this email. Do not share this code with anyone.</p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">
                        Best regards,<br>
                        <strong>Pasugo Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _get_password_reset_html(self, otp_code: str) -> str:
        """HTML template for password reset OTP"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Password Reset Request</h2>
                    <p style="color: #666; font-size: 16px;">Your One-Time Password (OTP) to reset your password is:</p>
                    
                    <div style="background-color: #dc3545; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 14px; margin: 0 0 10px 0; color: #e0e0e0;">OTP Code</p>
                        <h1 style="font-size: 48px; letter-spacing: 5px; margin: 0; font-weight: bold;">{otp_code}</h1>
                    </div>
                    
                    <p style="color: #999; font-size: 14px; text-align: center;">This code is valid for 10 minutes</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 14px;">If you didn't request a password reset, please ignore this email and your account remains secure.</p>
                    
                    <p style="color: #999; font-size: 12px; margin-top: 20px;">
                        <strong>For security:</strong> Never share your OTP with anyone, including Pasugo support staff.
                    </p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">
                        Best regards,<br>
                        <strong>Pasugo Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _get_phone_verification_html(self, otp_code: str, phone_number: str = None) -> str:
        """HTML template for phone verification OTP"""
        phone_display = f"({phone_number})" if phone_number else ""
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Verify Your Phone Number</h2>
                    <p style="color: #666; font-size: 16px;">Your One-Time Password (OTP) to verify your phone number {phone_display} is:</p>
                    
                    <div style="background-color: #ffc107; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 14px; margin: 0 0 10px 0; color: #333;">OTP Code</p>
                        <h1 style="font-size: 48px; letter-spacing: 5px; margin: 0; font-weight: bold;">{otp_code}</h1>
                    </div>
                    
                    <p style="color: #999; font-size: 14px; text-align: center;">This code is valid for 10 minutes</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 14px;">If you didn't request this verification, please ignore this email.</p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">
                        Best regards,<br>
                        <strong>Pasugo Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """


# Create singleton instance
try:
    brevo_sender = BrevoEmailSender()
except Exception as e:
    logger.error(f"Failed to initialize BrevoEmailSender: {e}")
    brevo_sender = None