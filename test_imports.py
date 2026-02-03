#!/usr/bin/env python3
"""
Quick test to verify all imports work correctly
"""

try:
    print("Testing imports...")
    
    print("  ✓ Importing config...")
    from config import settings
    
    print("  ✓ Importing database...")
    from database import get_db, engine, SessionLocal, Base, init_db, check_db_connection
    
    print("  ✓ Importing models...")
    from models import (
        User, Rider, BillRequest, Payment, Rating, OTP, Complaint,
        Notification, UserSession, AdminUser, UserDevice, 
        UserLoginHistory, UserPreference, RiderTask, PasswordResetToken
    )
    
    print("  ✓ Importing security utilities...")
    from utils.security import hash_password, verify_password, create_access_token, verify_token
    
    print("  ✓ Importing dependencies...")
    from utils.dependencies import get_current_user, get_current_active_user
    
    print("  ✓ Importing routes...")
    from routes import (
        auth_router, users_router, bill_requests_router,
        riders_router, complaints_router, notifications_router, payments_router
    )
    
    print("  ✓ Importing FastAPI app...")
    from app import app
    
    print("\n✅ All imports successful!")
    
    print("\nDatabase Configuration:")
    print(f"  Host: {settings.DB_HOST}")
    print(f"  Port: {settings.DB_PORT}")
    print(f"  Database: {settings.DB_NAME}")
    print(f"  Debug: {settings.DEBUG}")
    
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
