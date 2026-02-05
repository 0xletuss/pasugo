from .auth import router as auth_router
from .users import router as users_router
from .bill_requests import router as bill_requests_router
from .riders import router as riders_router
from .complaints import router as complaints_router
from .notifications import router as notifications_router
from .payments import router as payments_router
from .uploads import router as uploads_router

__all__ = [
    "auth_router",
    "users_router",
    "bill_requests_router",
    "riders_router",
    "complaints_router",
    "notifications_router",
    "payments_router",
    "uploads_router",
]