"""
routes/locations.py - User Location and Available Riders Routes (FastAPI)
Handles location tracking and displaying available riders on customer map
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import math
from decimal import Decimal

from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from routes.auth import get_current_user
from models.user import User

# Create router
router = APIRouter(prefix="/locations", tags=["locations"])


# ============================================
# PYDANTIC MODELS
# ============================================

class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[int] = Field(None, ge=0)
    address: Optional[str] = None
    request_id: Optional[int] = None


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


# ============================================
# LOCATION ENDPOINTS
# ============================================

@router.post("/update")
async def update_location(
    location: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's current location
    Called by both customers and riders to share location
    """
    try:
        user_id = current_user.user_id
        
        # Check if location exists for this user (within last hour)
        existing = db.execute(
            text("""
            SELECT location_id FROM user_locations
            WHERE user_id = :user_id 
            AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY created_at DESC
            LIMIT 1
            """),
            {"user_id": user_id}
        ).fetchone()

        if existing:
            # Update existing location
            db.execute(
                text("""
                UPDATE user_locations 
                SET latitude = :lat, longitude = :lng, accuracy = :acc, 
                    address = :addr, created_at = NOW()
                WHERE location_id = :location_id
                """),
                {
                    "lat": location.latitude,
                    "lng": location.longitude,
                    "acc": location.accuracy,
                    "addr": location.address,
                    "location_id": existing[0]
                }
            )
            location_id = existing[0]
        else:
            # Insert new location
            result = db.execute(
                text("""
                INSERT INTO user_locations 
                (user_id, request_id, latitude, longitude, accuracy, address)
                VALUES (:user_id, :request_id, :lat, :lng, :acc, :addr)
                """),
                {
                    "user_id": user_id,
                    "request_id": location.request_id,
                    "lat": location.latitude,
                    "lng": location.longitude,
                    "acc": location.accuracy,
                    "addr": location.address
                }
            )
            location_id = result.lastrowid

        db.commit()

        return {
            "success": True,
            "message": "Location updated successfully",
            "data": {
                "location_id": location_id,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/riders/available")
async def get_available_riders(
    lat: float = Query(..., description="Customer latitude"),
    lng: float = Query(..., description="Customer longitude"),
    radius: float = Query(20, ge=1, le=100, description="Search radius in km"),
    limit: int = Query(50, ge=1, le=200, description="Maximum riders to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all available riders with their locations
    Sorted by distance from customer's location
    """
    try:
        # Get available riders with their locations
        rows = db.execute(
            text("""
            SELECT 
                r.rider_id,
                u.user_id,
                u.full_name,
                u.phone_number,
                r.vehicle_type,
                r.license_plate,
                r.availability_status,
                r.rating,
                r.total_tasks_completed,
                ul.latitude,
                ul.longitude,
                ul.accuracy,
                ul.address,
                ul.created_at as last_location_update
            FROM riders r
            JOIN users u ON r.user_id = u.user_id
            LEFT JOIN user_locations ul ON u.user_id = ul.user_id
            WHERE r.availability_status IN ('available', 'busy')
            AND ul.created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY r.rating DESC
            LIMIT :limit
            """),
            {"limit": limit}
        ).fetchall()

        riders_list = []
        for row in rows:
            rider_lat = row[9]
            rider_lng = row[10]
            
            if rider_lat and rider_lng:
                distance = calculate_distance(lat, lng, float(rider_lat), float(rider_lng))
                
                # Filter by radius
                if distance <= radius:
                    riders_list.append({
                        "rider_id": row[0],
                        "user_id": row[1],
                        "full_name": row[2],
                        "phone_number": row[3],
                        "vehicle_type": row[4],
                        "license_plate": row[5],
                        "availability_status": row[6],
                        "rating": float(row[7]) if row[7] else 0.0,
                        "total_tasks_completed": row[8],
                        "latitude": float(rider_lat),
                        "longitude": float(rider_lng),
                        "accuracy": row[11],
                        "address": row[12],
                        "distance_km": round(distance, 2),
                        "last_location_update": row[13].isoformat() if row[13] else None
                    })

        # Sort by distance
        riders_list.sort(key=lambda r: r["distance_km"])

        return {
            "success": True,
            "riders": riders_list,
            "count": len(riders_list),
            "search_params": {
                "latitude": lat,
                "longitude": lng,
                "radius_km": radius
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/riders/nearby")
async def get_nearby_riders(
    lat: float = Query(..., description="Customer latitude"),
    lng: float = Query(..., description="Customer longitude"),
    radius: float = Query(5, ge=1, le=100, description="Search radius in km"),
    status: str = Query("available", description="Availability status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get riders within a specific radius and availability status"""
    try:
        # Validate status
        valid_statuses = ["available", "busy", "all"]
        if status not in valid_statuses:
            status = "available"

        # Build status filter
        if status == "all":
            status_filter = "r.availability_status IN ('available', 'busy', 'offline')"
        else:
            status_filter = f"r.availability_status = '{status}'"

        query = f"""
            SELECT 
                r.rider_id,
                u.user_id,
                u.full_name,
                u.phone_number,
                r.vehicle_type,
                r.license_plate,
                r.availability_status,
                r.rating,
                r.total_tasks_completed,
                ul.latitude,
                ul.longitude,
                ul.accuracy,
                ul.address,
                ul.created_at as last_location_update
            FROM riders r
            JOIN users u ON r.user_id = u.user_id
            LEFT JOIN user_locations ul ON u.user_id = ul.user_id
            WHERE {status_filter}
            AND ul.created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY r.rating DESC, r.rider_id
        """

        rows = db.execute(text(query)).fetchall()

        riders_list = []
        for row in rows:
            rider_lat = row[9]
            rider_lng = row[10]
            
            if rider_lat and rider_lng:
                distance = calculate_distance(lat, lng, float(rider_lat), float(rider_lng))
                
                if distance <= radius:
                    riders_list.append({
                        "rider_id": row[0],
                        "user_id": row[1],
                        "full_name": row[2],
                        "phone_number": row[3],
                        "vehicle_type": row[4],
                        "license_plate": row[5],
                        "availability_status": row[6],
                        "rating": float(row[7]) if row[7] else 0.0,
                        "total_tasks_completed": row[8],
                        "latitude": float(rider_lat),
                        "longitude": float(rider_lng),
                        "accuracy": row[11],
                        "address": row[12],
                        "distance_km": round(distance, 2),
                        "last_location_update": row[13].isoformat() if row[13] else None
                    })

        riders_list.sort(key=lambda r: r["distance_km"])

        return {
            "success": True,
            "riders": riders_list,
            "count": len(riders_list),
            "search_radius_km": radius,
            "status_filter": status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/riders/{rider_id}")
async def get_rider_location(
    rider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific rider's location with details"""
    try:
        row = db.execute(
            text("""
            SELECT 
                r.rider_id,
                u.user_id,
                u.full_name,
                u.phone_number,
                r.vehicle_type,
                r.license_plate,
                r.availability_status,
                r.rating,
                r.total_tasks_completed,
                ul.latitude,
                ul.longitude,
                ul.accuracy,
                ul.address,
                ul.created_at as last_location_update
            FROM riders r
            JOIN users u ON r.user_id = u.user_id
            LEFT JOIN user_locations ul ON u.user_id = ul.user_id
            WHERE r.rider_id = :rider_id
            """),
            {"rider_id": rider_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rider not found")

        return {
            "success": True,
            "data": {
                "rider_id": row[0],
                "user_id": row[1],
                "full_name": row[2],
                "phone_number": row[3],
                "vehicle_type": row[4],
                "license_plate": row[5],
                "availability_status": row[6],
                "rating": float(row[7]) if row[7] else 0.0,
                "total_tasks_completed": row[8],
                "latitude": float(row[9]) if row[9] else None,
                "longitude": float(row[10]) if row[10] else None,
                "accuracy": row[11],
                "address": row[12],
                "last_location_update": row[13].isoformat() if row[13] else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user_location(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a user's latest location"""
    try:
        # Authorization: can view own location or admin
        if current_user.user_id != user_id and str(current_user.user_type) != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized")

        row = db.execute(
            text("""
            SELECT location_id, user_id, request_id, latitude, longitude, 
                   accuracy, address, created_at
            FROM user_locations
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
            """),
            {"user_id": user_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Location not found")

        return {
            "success": True,
            "data": {
                "location_id": row[0],
                "user_id": row[1],
                "request_id": row[2],
                "latitude": float(row[3]),
                "longitude": float(row[4]),
                "accuracy": row[5],
                "address": row[6],
                "created_at": row[7].isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def location_health():
    """Health check endpoint for location service"""
    return {
        "success": True,
        "status": "healthy",
        "service": "locations",
        "timestamp": datetime.utcnow().isoformat()
    }