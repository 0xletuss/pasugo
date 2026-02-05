from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
import uvicorn
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routes
from routes import (
    auth_router,
    users_router,
    bill_requests_router,
    riders_router,
    complaints_router,
    notifications_router,
    payments_router,
    uploads_router
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Pasugo - Bill Payment and Delivery Service API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    logger.error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/")
def root():
    return {
        "success": True,
        "message": "Pasugo API is running",
        "version": settings.APP_VERSION
    }


@app.get("/health")
def health_check():
    return {
        "success": True,
        "message": "Service is healthy",
        "status": "ok"
    }


@app.get("/health/db")
def health_check_db():
    """Check database connectivity"""
    try:
        from database import get_db
        from sqlalchemy.orm import Session
        db = next(get_db())
        # Try a simple query
        db.execute("SELECT 1")
        return {
            "success": True,
            "message": "Database connection successful",
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": "Database connection failed",
            "error": str(e),
            "status": "error"
        }


# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(bill_requests_router, prefix="/api")
app.include_router(riders_router, prefix="/api")
app.include_router(complaints_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")


# Startup event
@app.on_event("startup")
def startup_event():
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} is starting...")
    logger.info(f"📚 Documentation available at: /docs")
    logger.info(f"🔗 Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    # Initialize database tables
    try:
        from database import init_db
        logger.info("📊 Initializing database tables...")
        init_db()
        logger.info("✅ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}", exc_info=True)
    
    logger.info("✅ API ready to receive requests")
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} is starting...")
    print(f"📚 Documentation available at: /docs")
    print(f"🔗 Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print("✅ API ready to receive requests")


# Shutdown event
@app.on_event("shutdown")
def shutdown_event():
    print("👋 Shutting down Pasugo API...")


# Run the application
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )