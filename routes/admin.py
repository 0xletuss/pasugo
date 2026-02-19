"""
routes/admin.py  –  Admin Dashboard API

Revenue split: 70 % rider / 30 % admin on every service_fee.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date, case, desc, and_, text as sa_text
from database import get_db
from models.user import User, UserType
from models.rider import Rider, RiderStatus
from models.request import Request, RequestStatus, ServiceType
from models.notification import Notification
from models.admin_user import AdminUser
from utils.dependencies import get_current_active_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# ── Revenue split constants ──────────────────────────────────────────────────
RIDER_SHARE_PCT  = Decimal("0.70")
ADMIN_SHARE_PCT  = Decimal("0.30")


# ── Helper: require admin ────────────────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.user_type != UserType.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERVIEW / DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/summary")
def dashboard_summary(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Returns high-level KPIs for the admin landing page:
    total riders, customers, requests, revenue, admin share, etc.
    """
    total_riders     = db.query(func.count(Rider.rider_id)).scalar() or 0
    total_customers  = db.query(func.count(User.user_id)).filter(User.user_type == UserType.customer).scalar() or 0
    total_users      = db.query(func.count(User.user_id)).scalar() or 0

    total_requests   = db.query(func.count(Request.request_id)).scalar() or 0
    completed        = db.query(func.count(Request.request_id)).filter(Request.status == RequestStatus.completed).scalar() or 0
    pending          = db.query(func.count(Request.request_id)).filter(Request.status == RequestStatus.pending).scalar() or 0
    in_progress      = db.query(func.count(Request.request_id)).filter(Request.status == RequestStatus.in_progress).scalar() or 0
    cancelled        = db.query(func.count(Request.request_id)).filter(Request.status == RequestStatus.cancelled).scalar() or 0

    # Revenue from completed requests
    total_service_fee = db.query(func.coalesce(func.sum(Request.service_fee), 0)).filter(
        Request.status == RequestStatus.completed,
        Request.service_fee.isnot(None),
    ).scalar()
    total_service_fee = Decimal(str(total_service_fee))

    total_item_cost = db.query(func.coalesce(func.sum(Request.item_cost), 0)).filter(
        Request.status == RequestStatus.completed,
        Request.item_cost.isnot(None),
    ).scalar()

    total_amount_sum = db.query(func.coalesce(func.sum(Request.total_amount), 0)).filter(
        Request.status == RequestStatus.completed,
        Request.total_amount.isnot(None),
    ).scalar()

    admin_share = float(total_service_fee * ADMIN_SHARE_PCT)
    rider_share = float(total_service_fee * RIDER_SHARE_PCT)

    # Today's stats
    today = date.today()
    today_requests = db.query(func.count(Request.request_id)).filter(
        cast(Request.created_at, Date) == today
    ).scalar() or 0
    today_completed = db.query(func.count(Request.request_id)).filter(
        cast(Request.completed_at, Date) == today,
        Request.status == RequestStatus.completed,
    ).scalar() or 0
    today_revenue = db.query(func.coalesce(func.sum(Request.service_fee), 0)).filter(
        cast(Request.completed_at, Date) == today,
        Request.status == RequestStatus.completed,
    ).scalar()
    today_revenue = float(Decimal(str(today_revenue)))

    return {
        "success": True,
        "data": {
            "total_riders": total_riders,
            "total_customers": total_customers,
            "total_users": total_users,
            "total_requests": total_requests,
            "completed_requests": completed,
            "pending_requests": pending,
            "in_progress_requests": in_progress,
            "cancelled_requests": cancelled,
            "total_service_fee": float(total_service_fee),
            "total_item_cost": float(total_item_cost),
            "total_amount": float(total_amount_sum),
            "admin_share": admin_share,
            "rider_share": rider_share,
            "today": {
                "requests": today_requests,
                "completed": today_completed,
                "revenue": today_revenue,
                "admin_share": round(today_revenue * 0.30, 2),
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  REVENUE ANALYTICS  (daily / weekly / monthly trend)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/revenue")
def revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Daily revenue breakdown for the past *days* days."""
    since = date.today() - timedelta(days=days - 1)

    rows = (
        db.query(
            cast(Request.completed_at, Date).label("day"),
            func.count(Request.request_id).label("deliveries"),
            func.coalesce(func.sum(Request.service_fee), 0).label("service_fee"),
            func.coalesce(func.sum(Request.item_cost), 0).label("item_cost"),
            func.coalesce(func.sum(Request.total_amount), 0).label("total_amount"),
        )
        .filter(
            Request.status == RequestStatus.completed,
            Request.completed_at.isnot(None),
            cast(Request.completed_at, Date) >= since,
        )
        .group_by(cast(Request.completed_at, Date))
        .order_by(cast(Request.completed_at, Date))
        .all()
    )

    trend = []
    for r in rows:
        sf = float(r.service_fee)
        trend.append({
            "date": str(r.day),
            "deliveries": r.deliveries,
            "service_fee": sf,
            "item_cost": float(r.item_cost),
            "total_amount": float(r.total_amount),
            "admin_share": round(sf * 0.30, 2),
            "rider_share": round(sf * 0.70, 2),
        })

    return {"success": True, "data": trend}


# ═══════════════════════════════════════════════════════════════════════════════
#  SERVICE-TYPE BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/service-types")
def service_type_breakdown(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Request.service_type,
            func.count(Request.request_id).label("count"),
            func.coalesce(func.sum(Request.service_fee), 0).label("total_fee"),
        )
        .filter(Request.status == RequestStatus.completed)
        .group_by(Request.service_type)
        .all()
    )
    return {
        "success": True,
        "data": [
            {"service_type": str(r.service_type.value) if r.service_type else "unknown",
             "count": r.count,
             "total_fee": float(r.total_fee)}
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CUSTOMER ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/customers")
def customer_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(User.user_id)).filter(User.user_type == UserType.customer).scalar() or 0
    active = db.query(func.count(User.user_id)).filter(User.user_type == UserType.customer, User.is_active == True).scalar() or 0

    # New customers per day (last 30 days)
    since = date.today() - timedelta(days=29)
    daily = (
        db.query(
            cast(User.created_at, Date).label("day"),
            func.count(User.user_id).label("new_customers"),
        )
        .filter(User.user_type == UserType.customer, cast(User.created_at, Date) >= since)
        .group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
        .all()
    )

    # Top customers by request count
    top = (
        db.query(
            User.user_id,
            User.full_name,
            User.email,
            func.count(Request.request_id).label("request_count"),
            func.coalesce(func.sum(Request.total_amount), 0).label("total_spent"),
        )
        .join(Request, Request.customer_id == User.user_id)
        .filter(Request.status == RequestStatus.completed)
        .group_by(User.user_id, User.full_name, User.email)
        .order_by(desc("request_count"))
        .limit(10)
        .all()
    )

    return {
        "success": True,
        "data": {
            "total_customers": total,
            "active_customers": active,
            "daily_signups": [{"date": str(d.day), "count": d.new_customers} for d in daily],
            "top_customers": [
                {"user_id": t.user_id, "name": t.full_name, "email": t.email,
                 "requests": t.request_count, "total_spent": float(t.total_spent)}
                for t in top
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  RIDERS LIST  (with revenue per rider)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/riders")
def list_riders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all riders with their revenue breakdown.
    Revenue split: service_fee × 70 % rider / 30 % admin.
    """
    q = db.query(Rider).options(joinedload(Rider.user))

    if status_filter:
        try:
            rs = RiderStatus(status_filter)
            q = q.filter(Rider.availability_status == rs)
        except ValueError:
            pass

    if search:
        q = q.join(User, Rider.user_id == User.user_id).filter(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )

    total = q.count()
    riders = q.order_by(Rider.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for rider in riders:
        # Compute rider revenue from completed requests
        stats = db.query(
            func.count(Request.request_id).label("total_deliveries"),
            func.coalesce(func.sum(Request.service_fee), 0).label("total_service_fee"),
            func.coalesce(func.sum(Request.total_amount), 0).label("total_amount"),
        ).filter(
            Request.rider_id == rider.rider_id,
            Request.status == RequestStatus.completed,
        ).first()

        # Today's deliveries
        today_deliveries = db.query(func.count(Request.request_id)).filter(
            Request.rider_id == rider.rider_id,
            Request.status == RequestStatus.completed,
            cast(Request.completed_at, Date) == date.today(),
        ).scalar() or 0

        sf = float(stats.total_service_fee)
        result.append({
            "rider_id": rider.rider_id,
            "user_id": rider.user_id,
            "full_name": rider.user.full_name if rider.user else None,
            "email": rider.user.email if rider.user else None,
            "phone": rider.user.phone_number if rider.user else None,
            "vehicle_type": rider.vehicle_type,
            "vehicle_plate": rider.vehicle_plate,
            "license_number": rider.license_number,
            "status": rider.availability_status.value if rider.availability_status else "offline",
            "rating": float(rider.rating) if rider.rating else 0,
            "total_deliveries": stats.total_deliveries,
            "today_deliveries": today_deliveries,
            "total_service_fee": sf,
            "rider_share": round(sf * 0.70, 2),
            "admin_share": round(sf * 0.30, 2),
            "total_amount_handled": float(stats.total_amount),
            "gcash_name": rider.gcash_name,
            "gcash_number": rider.gcash_number,
            "created_at": str(rider.created_at) if rider.created_at else None,
        })

    return {
        "success": True,
        "data": result,
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  SINGLE RIDER DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/riders/{rider_id}")
def get_rider_detail(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rider = db.query(Rider).options(joinedload(Rider.user)).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # All deliveries for this rider (recent 50)
    recent = (
        db.query(Request)
        .filter(Request.rider_id == rider_id, Request.status == RequestStatus.completed)
        .order_by(Request.completed_at.desc())
        .limit(50)
        .all()
    )

    deliveries = []
    for req in recent:
        sf = float(req.service_fee) if req.service_fee else 0
        deliveries.append({
            "request_id": req.request_id,
            "service_type": req.service_type.value if req.service_type else None,
            "item_cost": float(req.item_cost) if req.item_cost else 0,
            "service_fee": sf,
            "total_amount": float(req.total_amount) if req.total_amount else 0,
            "rider_share": round(sf * 0.70, 2),
            "admin_share": round(sf * 0.30, 2),
            "completed_at": str(req.completed_at) if req.completed_at else None,
            "delivery_address": req.delivery_address,
        })

    # Daily breakdown for this rider (last 30 days)
    since = date.today() - timedelta(days=29)
    daily = (
        db.query(
            cast(Request.completed_at, Date).label("day"),
            func.count(Request.request_id).label("deliveries"),
            func.coalesce(func.sum(Request.service_fee), 0).label("service_fee"),
        )
        .filter(
            Request.rider_id == rider_id,
            Request.status == RequestStatus.completed,
            Request.completed_at.isnot(None),
            cast(Request.completed_at, Date) >= since,
        )
        .group_by(cast(Request.completed_at, Date))
        .order_by(cast(Request.completed_at, Date))
        .all()
    )

    total_sf = sum(d.service_fee for d in deliveries) if deliveries else 0

    return {
        "success": True,
        "data": {
            "rider_id": rider.rider_id,
            "full_name": rider.user.full_name if rider.user else None,
            "email": rider.user.email if rider.user else None,
            "phone": rider.user.phone_number if rider.user else None,
            "vehicle_type": rider.vehicle_type,
            "vehicle_plate": rider.vehicle_plate,
            "license_number": rider.license_number,
            "status": rider.availability_status.value if rider.availability_status else "offline",
            "rating": float(rider.rating) if rider.rating else 0,
            "gcash_name": rider.gcash_name,
            "gcash_number": rider.gcash_number,
            "total_deliveries": len(deliveries),
            "total_service_fee": float(total_sf),
            "rider_share": round(float(total_sf) * 0.70, 2),
            "admin_share": round(float(total_sf) * 0.30, 2),
            "created_at": str(rider.created_at) if rider.created_at else None,
            "recent_deliveries": deliveries,
            "daily_breakdown": [
                {"date": str(d.day), "deliveries": d.deliveries,
                 "service_fee": float(d.service_fee),
                 "rider_share": round(float(d.service_fee) * 0.70, 2),
                 "admin_share": round(float(d.service_fee) * 0.30, 2)}
                for d in daily
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  RIDER DAILY DELIVERIES  (for a specific date)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/riders/{rider_id}/deliveries")
def rider_deliveries_by_date(
    rider_id: int,
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    if target_date:
        try:
            dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        dt = date.today()

    reqs = (
        db.query(Request)
        .filter(
            Request.rider_id == rider_id,
            Request.status == RequestStatus.completed,
            cast(Request.completed_at, Date) == dt,
        )
        .order_by(Request.completed_at.desc())
        .all()
    )

    items = []
    total_fee = 0
    for r in reqs:
        sf = float(r.service_fee) if r.service_fee else 0
        total_fee += sf
        items.append({
            "request_id": r.request_id,
            "service_type": r.service_type.value if r.service_type else None,
            "item_cost": float(r.item_cost) if r.item_cost else 0,
            "service_fee": sf,
            "total_amount": float(r.total_amount) if r.total_amount else 0,
            "rider_share": round(sf * 0.70, 2),
            "admin_share": round(sf * 0.30, 2),
            "completed_at": str(r.completed_at) if r.completed_at else None,
        })

    return {
        "success": True,
        "date": str(dt),
        "data": {
            "deliveries": items,
            "summary": {
                "count": len(items),
                "total_service_fee": total_fee,
                "rider_share": round(total_fee * 0.70, 2),
                "admin_share": round(total_fee * 0.30, 2),
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  RIDER LOCATION (current + history)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/riders/{rider_id}/location")
def rider_location(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Latest location
    latest = db.execute(
        sa_text("""
            SELECT location_id, latitude, longitude, accuracy, address, created_at
            FROM user_locations
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"uid": rider.user_id},
    ).fetchone()

    # History (last 50 points)
    history = db.execute(
        sa_text("""
            SELECT location_id, latitude, longitude, accuracy, address, created_at
            FROM user_locations
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {"uid": rider.user_id},
    ).fetchall()

    def loc_dict(row):
        return {
            "location_id": row[0],
            "latitude": float(row[1]),
            "longitude": float(row[2]),
            "accuracy": row[3],
            "address": row[4],
            "created_at": str(row[5]) if row[5] else None,
        }

    return {
        "success": True,
        "data": {
            "current": loc_dict(latest) if latest else None,
            "history": [loc_dict(h) for h in history],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DELETE RIDER
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/riders/{rider_id}")
def delete_rider(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rider = db.query(Rider).options(joinedload(Rider.user)).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rider_name = rider.user.full_name if rider.user else f"Rider #{rider_id}"

    # Check for active (non-completed, non-cancelled) requests
    active_reqs = db.query(func.count(Request.request_id)).filter(
        Request.rider_id == rider_id,
        Request.status.notin_([RequestStatus.completed, RequestStatus.cancelled]),
    ).scalar()
    if active_reqs > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rider has {active_reqs} active request(s). Complete or cancel them first.",
        )

    # Deactivate the user account (soft delete)
    if rider.user:
        rider.user.is_active = False
    rider.availability_status = RiderStatus.suspended

    db.commit()
    logger.info(f"Admin {admin.email} suspended rider {rider_id} ({rider_name})")

    return {
        "success": True,
        "message": f"Rider '{rider_name}' has been suspended and account deactivated.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  RECENT REQUESTS (admin overview)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/requests")
def admin_list_requests(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Request)

    if status_filter:
        try:
            rs = RequestStatus(status_filter)
            q = q.filter(Request.status == rs)
        except ValueError:
            pass

    total = q.count()
    reqs = q.order_by(Request.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for r in reqs:
        sf = float(r.service_fee) if r.service_fee else 0
        items.append({
            "request_id": r.request_id,
            "customer_id": r.customer_id,
            "rider_id": r.rider_id,
            "service_type": r.service_type.value if r.service_type else None,
            "status": r.status.value if r.status else None,
            "item_cost": float(r.item_cost) if r.item_cost else 0,
            "service_fee": sf,
            "total_amount": float(r.total_amount) if r.total_amount else 0,
            "admin_share": round(sf * 0.30, 2),
            "rider_share": round(sf * 0.70, 2),
            "created_at": str(r.created_at) if r.created_at else None,
            "completed_at": str(r.completed_at) if r.completed_at else None,
        })

    return {
        "success": True,
        "data": items,
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN LOGIN  (uses same JWT as regular users, but checks admin type)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me")
def admin_me(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    admin_profile = db.query(AdminUser).filter(AdminUser.user_id == admin.user_id).first()
    return {
        "success": True,
        "data": {
            "user_id": admin.user_id,
            "full_name": admin.full_name,
            "email": admin.email,
            "user_type": admin.user_type.value,
            "role": admin_profile.role.value if admin_profile else "admin",
        },
    }
