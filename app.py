from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
import uvicorn

# Import routes
from routes import (
    auth_router,
    users_router,
    bill_requests_router,
    riders_router,
    complaints_router,
    notifications_router,
    payments_router
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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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


# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(bill_requests_router)
app.include_router(riders_router)
app.include_router(complaints_router)
app.include_router(notifications_router)
app.include_router(payments_router)


# Startup event
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} is starting...")
    print(f"📚 Documentation available at: http://localhost:8000/docs")
    print(f"🔗 Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Shutting down Pasugo API...")


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=10000,
        reload=settings.DEBUG
    )