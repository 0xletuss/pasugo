"""
routes/locations.py - User Location and Available Riders Routes
Handles location tracking and displaying available riders on customer map
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from decimal import Decimal
import math
from typing import List, Dict, Tuple

from models.location import UserLocation, AvailableRider, LocationHistory
from models.rider import Rider
from models.user import User
from utils.dependencies import get_db
from utils.security import token_required
from utils.responses import success_response, error_response

locations_bp = Blueprint("locations", __name__, url_prefix="/api/locations")


# ============================================
# LOCATION MANAGEMENT ENDPOINTS
# ============================================


@locations_bp.route("/update", methods=["POST"])
@token_required
def update_location(current_user):
    """
    Update user's current location
    Called by both customers and riders to share location
    
    POST /api/locations/update
    Body: {
        "latitude": 14.5995,
        "longitude": 120.9842,
        "accuracy": 15,
        "address": "Manila, NCR"
    }
    
    Returns:
        Location update confirmation
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return error_response("Request body is required", 400)

        latitude = data.get("latitude")
        longitude = data.get("longitude")
        accuracy = data.get("accuracy")
        address = data.get("address")
        request_id = data.get("request_id")

        # Validate coordinates
        if latitude is None or longitude is None:
            return error_response(
                "Latitude and longitude are required", 400
            )

        try:
            lat = float(latitude)
            lng = float(longitude)

            # Validate ranges
            if lat < -90 or lat > 90:
                return error_response(
                    "Latitude must be between -90 and 90", 400
                )
            if lng < -180 or lng > 180:
                return error_response(
                    "Longitude must be between -180 and 180", 400
                )
        except (ValueError, TypeError):
            return error_response(
                "Latitude and longitude must be valid numbers", 400
            )

        # Validate accuracy if provided
        if accuracy is not None:
            try:
                accuracy = int(accuracy)
                if accuracy < 0:
                    return error_response(
                        "Accuracy must be positive", 400
                    )
            except (ValueError, TypeError):
                accuracy = None

        db = get_db()
        cursor = db.cursor()

        try:
            # Check if location record exists for this user (created in last hour)
            cursor.execute(
                """
                SELECT location_id FROM user_locations
                WHERE user_id = %s 
                AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (current_user["user_id"],),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing location
                location_id = existing[0]
                cursor.execute(
                    """
                    UPDATE user_locations 
                    SET latitude = %s, longitude = %s, accuracy = %s, 
                        address = %s, created_at = NOW()
                    WHERE location_id = %s
                    """,
                    (lat, lng, accuracy, address, location_id),
                )
            else:
                # Insert new location
                cursor.execute(
                    """
                    INSERT INTO user_locations 
                    (user_id, request_id, latitude, longitude, accuracy, address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (current_user["user_id"], request_id, lat, lng, accuracy, address),
                )
                location_id = cursor.lastrowid

            db.commit()

            return success_response(
                {
                    "message": "Location updated successfully",
                    "location_id": location_id,
                    "latitude": lat,
                    "longitude": lng,
                    "accuracy": accuracy,
                },
                201,
            )

        except Exception as db_error:
            db.rollback()
            return error_response(f"Database error: {str(db_error)}", 500)

    except Exception as e:
        return error_response(f"Error updating location: {str(e)}", 500)


@locations_bp.route("/<int:user_id>", methods=["GET"])
@token_required
def get_user_location(current_user, user_id):
    """
    Get a user's latest location
    
    GET /api/locations/1
    
    Returns:
        User's latest location data
    """
    try:
        # Authorization: can view own location or admin
        if (
            current_user["user_id"] != user_id
            and current_user.get("user_type") != "admin"
        ):
            return error_response("Unauthorized", 403)

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT location_id, user_id, request_id, latitude, longitude, 
                   accuracy, address, map_style_preference, created_at
            FROM user_locations
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()

        if not row:
            return error_response("Location not found", 404)

        location = UserLocation.from_db_row(row)
        return success_response(location.to_dict())

    except Exception as e:
        return error_response(f"Error fetching location: {str(e)}", 500)


@locations_bp.route("/history/<int:user_id>", methods=["GET"])
@token_required
def get_location_history(current_user, user_id):
    """
    Get user's location history (last 24 hours)
    
    GET /api/locations/history/1?limit=50
    
    Query Parameters:
        limit: Maximum records to return (default: 50, max: 200)
        hours: Hours to look back (default: 24)
    
    Returns:
        List of location history records
    """
    try:
        # Authorization check
        if (
            current_user["user_id"] != user_id
            and current_user.get("user_type") != "admin"
        ):
            return error_response("Unauthorized", 403)

        limit = min(int(request.args.get("limit", 50)), 200)
        hours = int(request.args.get("hours", 24))

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT location_id, user_id, request_id, latitude, longitude, 
                   accuracy, address, map_style_preference, created_at
            FROM user_locations
            WHERE user_id = %s 
            AND created_at > DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, hours, limit),
        )

        rows = cursor.fetchall()

        locations = [UserLocation.from_db_row(row).to_dict() for row in rows]

        return success_response({"locations": locations, "count": len(locations)})

    except Exception as e:
        return error_response(f"Error fetching location history: {str(e)}", 500)


# ============================================
# AVAILABLE RIDERS ENDPOINTS
# ============================================


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
    
    Returns:
        Distance in kilometers
    """
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


@locations_bp.route("/riders/available", methods=["GET"])
@token_required
def get_available_riders(current_user):
    """
    Get all available riders with their locations
    Sorted by distance from customer's location
    
    GET /api/locations/riders/available?lat=14.5995&lng=120.9842&radius=10
    
    Query Parameters:
        lat: Customer latitude (required)
        lng: Customer longitude (required)
        radius: Search radius in kilometers (default: 20, max: 100)
        limit: Maximum riders to return (default: 50)
    
    Returns:
        List of available riders with location data
    """
    try:
        # Get customer location
        lat = request.args.get("lat")
        lng = request.args.get("lng")
        radius = float(request.args.get("radius", 20))
        limit = min(int(request.args.get("limit", 50)), 200)

        if not lat or not lng:
            return error_response("Latitude and longitude are required", 400)

        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return error_response(
                "Latitude and longitude must be valid numbers", 400
            )

        # Validate radius
        if radius < 1 or radius > 100:
            radius = max(1, min(100, radius))

        db = get_db()
        cursor = db.cursor()

        # Get available riders with their locations
        cursor.execute(
            """
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
            LIMIT %s
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        riders_list = []
        for row in rows:
            rider = AvailableRider.from_db_row(row)

            # Calculate distance
            if rider.latitude and rider.longitude:
                distance = calculate_distance(
                    lat, lng, float(rider.latitude), float(rider.longitude)
                )

                # Filter by radius
                if distance <= radius:
                    rider.distance_km = Decimal(str(round(distance, 2)))
                    riders_list.append(rider.to_dict())

        # Sort by distance
        riders_list.sort(key=lambda r: r["distance_km"] or float("inf"))

        return success_response(
            {
                "success": True,
                "riders": riders_list,
                "count": len(riders_list),
                "search_params": {
                    "latitude": lat,
                    "longitude": lng,
                    "radius_km": radius,
                },
            }
        )

    except Exception as e:
        return error_response(f"Error fetching available riders: {str(e)}", 500)


@locations_bp.route("/riders/nearby", methods=["GET"])
@token_required
def get_nearby_riders(current_user):
    """
    Get riders within a specific radius and availability status
    
    GET /api/locations/riders/nearby?lat=14.5995&lng=120.9842&radius=5&status=available
    
    Query Parameters:
        lat: Customer latitude (required)
        lng: Customer longitude (required)
        radius: Search radius in kilometers (default: 5)
        status: Availability status - 'available', 'busy', or 'all' (default: 'available')
    
    Returns:
        List of nearby riders
    """
    try:
        lat = request.args.get("lat")
        lng = request.args.get("lng")
        radius = float(request.args.get("radius", 5))
        status = request.args.get("status", "available").lower()

        if not lat or not lng:
            return error_response("Latitude and longitude are required", 400)

        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return error_response(
                "Latitude and longitude must be valid numbers", 400
            )

        # Validate status
        valid_statuses = ["available", "busy", "all"]
        if status not in valid_statuses:
            status = "available"

        db = get_db()
        cursor = db.cursor()

        # Build status filter
        if status == "all":
            status_filter = "IN ('available', 'busy', 'offline')"
        else:
            status_filter = f"= '{status}'"

        cursor.execute(
            f"""
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
            WHERE r.availability_status {status_filter}
            AND ul.created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY r.rating DESC, r.rider_id
            """,
        )

        rows = cursor.fetchall()

        riders_list = []
        for row in rows:
            rider = AvailableRider.from_db_row(row)

            if rider.latitude and rider.longitude:
                distance = calculate_distance(
                    lat, lng, float(rider.latitude), float(rider.longitude)
                )

                if distance <= radius:
                    rider.distance_km = Decimal(str(round(distance, 2)))
                    riders_list.append(rider.to_dict())

        riders_list.sort(key=lambda r: r["distance_km"])

        return success_response(
            {
                "success": True,
                "riders": riders_list,
                "count": len(riders_list),
                "search_radius_km": radius,
                "status_filter": status,
            }
        )

    except Exception as e:
        return error_response(f"Error fetching nearby riders: {str(e)}", 500)


@locations_bp.route("/riders/<int:rider_id>", methods=["GET"])
@token_required
def get_rider_location(current_user, rider_id):
    """
    Get a specific rider's location with details
    
    GET /api/locations/riders/1
    
    Returns:
        Rider location and profile information
    """
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
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
            WHERE r.rider_id = %s
            """,
            (rider_id,),
        )

        row = cursor.fetchone()

        if not row:
            return error_response("Rider not found", 404)

        rider = AvailableRider.from_db_row(row)
        return success_response(rider.to_dict())

    except Exception as e:
        return error_response(f"Error fetching rider location: {str(e)}", 500)


# ============================================
# LOCATION CLEANUP (Admin/Background)
# ============================================


@locations_bp.route("/cleanup", methods=["POST"])
@token_required
def cleanup_old_locations(current_user):
    """
    Delete location records older than specified hours
    Admin only - used to clean up database
    
    POST /api/locations/cleanup
    Body: {
        "hours": 24,  # Delete locations older than 24 hours
        "dry_run": true  # If true, just show what would be deleted
    }
    
    Returns:
        Number of records deleted
    """
    try:
        # Admin only
        if current_user.get("user_type") != "admin":
            return error_response("Admin access required", 403)

        data = request.get_json() or {}
        hours = int(data.get("hours", 24))
        dry_run = data.get("dry_run", False)

        if hours < 1:
            hours = 24

        db = get_db()
        cursor = db.cursor()

        try:
            if dry_run:
                # Just count
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM user_locations
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                    """,
                    (hours,),
                )
                count = cursor.fetchone()[0]

                return success_response(
                    {
                        "message": f"Would delete {count} records",
                        "count": count,
                        "dry_run": True,
                    }
                )
            else:
                # Actually delete
                cursor.execute(
                    """
                    DELETE FROM user_locations
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                    """,
                    (hours,),
                )
                count = cursor.rowcount
                db.commit()

                return success_response(
                    {
                        "message": f"Deleted {count} old location records",
                        "count": count,
                    }
                )

        except Exception as db_error:
            db.rollback()
            return error_response(f"Database error: {str(db_error)}", 500)

    except Exception as e:
        return error_response(f"Error cleaning up locations: {str(e)}", 500)


# ============================================
# HEALTH CHECK
# ============================================


@locations_bp.route("/health", methods=["GET"])
def location_health():
    """Health check endpoint for location service"""
    return success_response(
        {
            "status": "healthy",
            "service": "locations",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )