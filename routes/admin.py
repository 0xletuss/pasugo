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
from models.remittance import Remittance, RemittanceStatus
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

        # Today's remittance status
        today_rem = db.query(Remittance).filter(
            Remittance.rider_id == rider.rider_id,
            Remittance.remittance_date == date.today(),
        ).first()

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
            "remit_status": today_rem.status.value if today_rem else ("pending" if today_deliveries > 0 else "no_earnings"),
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

    total_sf = sum(d["service_fee"] for d in deliveries) if deliveries else 0

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


# ═══════════════════════════════════════════════════════════════════════════════
#  SHARES & REMITTANCE
# ═══════════════════════════════════════════════════════════════════════════════

def _build_daily_snapshot(db: Session, target_date: date):
    """
    Compute each rider's completed-request totals for *target_date*.
    Returns a list of dicts ready for the frontend table.
    """
    rows = (
        db.query(
            Rider.rider_id,
            User.full_name,
            Rider.vehicle_plate,
            func.count(Request.request_id).label("total_deliveries"),
            func.coalesce(func.sum(Request.service_fee), 0).label("total_service_fee"),
        )
        .join(User, Rider.user_id == User.user_id)
        .outerjoin(
            Request,
            and_(
                Request.rider_id == Rider.rider_id,
                Request.status == RequestStatus.completed,
                cast(Request.completed_at, Date) == target_date,
            ),
        )
        .group_by(Rider.rider_id, User.full_name, Rider.vehicle_plate)
        .all()
    )

    # Fetch existing remittance records for that date
    existing = {
        r.rider_id: r
        for r in db.query(Remittance).filter(Remittance.remittance_date == target_date).all()
    }

    result = []
    for row in rows:
        fee = Decimal(str(row.total_service_fee))
        rider_share = (fee * RIDER_SHARE_PCT).quantize(Decimal("0.01"))
        admin_share = (fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))
        rem = existing.get(row.rider_id)

        result.append({
            "rider_id": row.rider_id,
            "rider_name": row.full_name,
            "vehicle_plate": row.vehicle_plate or "",
            "total_deliveries": row.total_deliveries,
            "total_service_fee": float(fee),
            "rider_share": float(rider_share),
            "admin_share": float(admin_share),
            "status": rem.status.value if rem else ("pending" if fee > 0 else "no_earnings"),
            "remitted_at": rem.remitted_at.isoformat() if rem and rem.remitted_at else None,
            "remittance_id": rem.remittance_id if rem else None,
            "notes": rem.notes if rem else None,
        })

    # Sort: pending with earnings first, then remitted, then no earnings
    priority = {"pending": 0, "remitted": 1, "waived": 1, "no_earnings": 2}
    result.sort(key=lambda x: (priority.get(x["status"], 9), -x["admin_share"]))
    return result


@router.get("/remittances/today")
def remittances_today(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
):
    """
    Show every rider's earnings & remittance status for a specific date (default: today).
    """
    try:
        d = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    snapshot = _build_daily_snapshot(db, d)

    total_admin = sum(r["admin_share"] for r in snapshot)
    total_collected = sum(r["admin_share"] for r in snapshot if r["status"] == "remitted")
    total_pending = sum(r["admin_share"] for r in snapshot if r["status"] == "pending")

    return {
        "success": True,
        "data": {
            "date": d.isoformat(),
            "riders": snapshot,
            "summary": {
                "total_admin_share": round(total_admin, 2),
                "total_collected": round(total_collected, 2),
                "total_pending": round(total_pending, 2),
                "riders_pending": sum(1 for r in snapshot if r["status"] == "pending"),
                "riders_remitted": sum(1 for r in snapshot if r["status"] == "remitted"),
            },
        },
    }


@router.post("/remittances/{rider_id}/remit")
def mark_remitted(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    notes: Optional[str] = Query(None),
):
    """
    Mark a rider's admin-share as collected (remitted) for a given date.
    Creates the remittance record if it doesn't exist, then sets status='remitted'.
    """
    try:
        d = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Compute day's totals
    agg = (
        db.query(
            func.count(Request.request_id).label("cnt"),
            func.coalesce(func.sum(Request.service_fee), 0).label("fee"),
        )
        .filter(
            Request.rider_id == rider_id,
            Request.status == RequestStatus.completed,
            cast(Request.completed_at, Date) == d,
        )
        .one()
    )
    total_fee = Decimal(str(agg.fee))
    if total_fee <= 0:
        raise HTTPException(status_code=400, detail="No earnings to remit for this date")

    # Upsert remittance record
    rem = (
        db.query(Remittance)
        .filter(Remittance.rider_id == rider_id, Remittance.remittance_date == d)
        .first()
    )
    if rem and rem.status == RemittanceStatus.remitted:
        raise HTTPException(status_code=400, detail="Already remitted for this date")

    rider_share = (total_fee * RIDER_SHARE_PCT).quantize(Decimal("0.01"))
    admin_share = (total_fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))

    if not rem:
        rem = Remittance(
            rider_id=rider_id,
            remittance_date=d,
            total_deliveries=agg.cnt,
            total_service_fee=total_fee,
            rider_share=rider_share,
            admin_share=admin_share,
            status=RemittanceStatus.remitted,
            remitted_at=datetime.utcnow(),
            received_by=admin.user_id,
            notes=notes,
        )
        db.add(rem)
    else:
        rem.total_deliveries = agg.cnt
        rem.total_service_fee = total_fee
        rem.rider_share = rider_share
        rem.admin_share = admin_share
        rem.status = RemittanceStatus.remitted
        rem.remitted_at = datetime.utcnow()
        rem.received_by = admin.user_id
        if notes:
            rem.notes = notes

    db.commit()
    db.refresh(rem)

    return {
        "success": True,
        "message": f"Remittance of ₱{float(admin_share):.2f} collected from rider #{rider_id}",
        "data": {
            "remittance_id": rem.remittance_id,
            "rider_id": rider_id,
            "date": d.isoformat(),
            "total_service_fee": float(total_fee),
            "rider_share": float(rider_share),
            "admin_share": float(admin_share),
            "status": rem.status.value,
            "remitted_at": rem.remitted_at.isoformat(),
        },
    }


@router.post("/remittances/{rider_id}/waive")
def waive_remittance(
    rider_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    target_date: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
):
    """Waive the admin share for a rider on a given date."""
    try:
        d = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rem = (
        db.query(Remittance)
        .filter(Remittance.rider_id == rider_id, Remittance.remittance_date == d)
        .first()
    )
    if rem and rem.status == RemittanceStatus.remitted:
        raise HTTPException(status_code=400, detail="Already remitted")

    if not rem:
        agg = (
            db.query(
                func.count(Request.request_id).label("cnt"),
                func.coalesce(func.sum(Request.service_fee), 0).label("fee"),
            )
            .filter(
                Request.rider_id == rider_id,
                Request.status == RequestStatus.completed,
                cast(Request.completed_at, Date) == d,
            )
            .one()
        )
        total_fee = Decimal(str(agg.fee))
        rem = Remittance(
            rider_id=rider_id,
            remittance_date=d,
            total_deliveries=agg.cnt,
            total_service_fee=total_fee,
            rider_share=(total_fee * RIDER_SHARE_PCT).quantize(Decimal("0.01")),
            admin_share=(total_fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01")),
        )
        db.add(rem)

    rem.status = RemittanceStatus.waived
    rem.remitted_at = datetime.utcnow()
    rem.received_by = admin.user_id
    if notes:
        rem.notes = notes

    db.commit()
    return {"success": True, "message": "Remittance waived"}


@router.get("/remittances/history")
def remittances_history(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    rider_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
):
    """Paginated history of all remittance records with filters."""
    q = db.query(Remittance).join(Rider, Remittance.rider_id == Rider.rider_id).join(User, Rider.user_id == User.user_id)

    if rider_id:
        q = q.filter(Remittance.rider_id == rider_id)
    if status_filter:
        try:
            q = q.filter(Remittance.status == RemittanceStatus(status_filter))
        except ValueError:
            pass
    if date_from:
        try:
            q = q.filter(Remittance.remittance_date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(Remittance.remittance_date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass

    total = q.count()
    records = q.order_by(desc(Remittance.remittance_date), desc(Remittance.created_at)).offset((page - 1) * limit).limit(limit).all()

    items = []
    for r in records:
        rider = r.rider
        user = rider.user if rider else None
        items.append({
            "remittance_id": r.remittance_id,
            "rider_id": r.rider_id,
            "rider_name": user.full_name if user else "Unknown",
            "date": r.remittance_date.isoformat(),
            "total_deliveries": r.total_deliveries,
            "total_service_fee": float(r.total_service_fee),
            "rider_share": float(r.rider_share),
            "admin_share": float(r.admin_share),
            "status": r.status.value,
            "remitted_at": r.remitted_at.isoformat() if r.remitted_at else None,
            "notes": r.notes,
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/shares/summary")
def shares_summary(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """
    Overall shares analytics: lifetime & per-period totals.
    """
    since = date.today() - timedelta(days=days)

    # Lifetime from completed requests
    lifetime = db.query(
        func.coalesce(func.sum(Request.service_fee), 0),
        func.count(Request.request_id),
    ).filter(Request.status == RequestStatus.completed).one()

    lifetime_fee = Decimal(str(lifetime[0]))
    lifetime_count = lifetime[1]

    # Period from completed requests
    period = db.query(
        func.coalesce(func.sum(Request.service_fee), 0),
        func.count(Request.request_id),
    ).filter(
        Request.status == RequestStatus.completed,
        cast(Request.completed_at, Date) >= since,
    ).one()

    period_fee = Decimal(str(period[0]))
    period_count = period[1]

    # Remittance collection stats
    collected = db.query(
        func.coalesce(func.sum(Remittance.admin_share), 0),
    ).filter(
        Remittance.status == RemittanceStatus.remitted,
    ).scalar()
    collected = Decimal(str(collected))

    collected_period = db.query(
        func.coalesce(func.sum(Remittance.admin_share), 0),
    ).filter(
        Remittance.status == RemittanceStatus.remitted,
        Remittance.remittance_date >= since,
    ).scalar()
    collected_period = Decimal(str(collected_period))

    # Per-rider breakdown (period)
    rider_rows = (
        db.query(
            Rider.rider_id,
            User.full_name,
            func.count(Request.request_id).label("deliveries"),
            func.coalesce(func.sum(Request.service_fee), 0).label("fee"),
        )
        .join(User, Rider.user_id == User.user_id)
        .outerjoin(
            Request,
            and_(
                Request.rider_id == Rider.rider_id,
                Request.status == RequestStatus.completed,
                cast(Request.completed_at, Date) >= since,
            ),
        )
        .group_by(Rider.rider_id, User.full_name)
        .having(func.count(Request.request_id) > 0)
        .order_by(desc("fee"))
        .limit(20)
        .all()
    )

    rider_breakdown = []
    for rr in rider_rows:
        fee = Decimal(str(rr.fee))
        rider_breakdown.append({
            "rider_id": rr.rider_id,
            "rider_name": rr.full_name,
            "deliveries": rr.deliveries,
            "total_fee": float(fee),
            "rider_share": float((fee * RIDER_SHARE_PCT).quantize(Decimal("0.01"))),
            "admin_share": float((fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))),
        })

    # Daily trend (last N days)
    daily_trend = (
        db.query(
            cast(Request.completed_at, Date).label("day"),
            func.count(Request.request_id).label("cnt"),
            func.coalesce(func.sum(Request.service_fee), 0).label("fee"),
        )
        .filter(
            Request.status == RequestStatus.completed,
            cast(Request.completed_at, Date) >= since,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    trend = [
        {
            "date": row.day.isoformat() if row.day else None,
            "deliveries": row.cnt,
            "total_fee": float(row.fee),
            "admin_share": float((Decimal(str(row.fee)) * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))),
            "rider_share": float((Decimal(str(row.fee)) * RIDER_SHARE_PCT).quantize(Decimal("0.01"))),
        }
        for row in daily_trend
    ]

    return {
        "success": True,
        "data": {
            "lifetime": {
                "total_service_fee": float(lifetime_fee),
                "admin_share": float((lifetime_fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))),
                "rider_share": float((lifetime_fee * RIDER_SHARE_PCT).quantize(Decimal("0.01"))),
                "total_deliveries": lifetime_count,
                "total_collected": float(collected),
                "uncollected": float((lifetime_fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01")) - collected),
            },
            "period": {
                "days": days,
                "total_service_fee": float(period_fee),
                "admin_share": float((period_fee * ADMIN_SHARE_PCT).quantize(Decimal("0.01"))),
                "rider_share": float((period_fee * RIDER_SHARE_PCT).quantize(Decimal("0.01"))),
                "total_deliveries": period_count,
                "total_collected": float(collected_period),
            },
            "rider_breakdown": rider_breakdown,
            "daily_trend": trend,
        },
    }
