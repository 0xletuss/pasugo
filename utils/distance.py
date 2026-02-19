# utils/distance.py
# Distance calculation using OpenRouteService (ORS) API
# Calculates driving distance between two GPS coordinates
# Used to auto-compute rider service fees

import logging
import math
from typing import Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

# Service fee tiers (distance in km -> fee in pesos)
SERVICE_FEE_TIERS = [
    (3, Decimal("30.00")),   # 0-3 km  = ₱30
    (6, Decimal("60.00")),   # 3-6 km  = ₱60
    (9, Decimal("90.00")),   # 6-9 km  = ₱90
]
# Beyond 9 km: ₱30 per additional 3 km bracket
FEE_PER_EXTRA_BRACKET = Decimal("30.00")
BRACKET_SIZE_KM = 3


def calculate_service_fee(distance_km: float) -> Decimal:
    """
    Calculate the service fee based on distance in kilometers.

    Fee tiers:
      1-3 km  = ₱30
      3-6 km  = ₱60
      6-9 km  = ₱90
      9-12 km = ₱120
      ... (+₱30 per 3 km)
    
    Minimum fee is ₱30 (even for <1 km).
    """
    if distance_km <= 0:
        return SERVICE_FEE_TIERS[0][1]  # Minimum ₱30

    for max_km, fee in SERVICE_FEE_TIERS:
        if distance_km <= max_km:
            return fee

    # Beyond the last tier: calculate extra brackets
    last_tier_km = SERVICE_FEE_TIERS[-1][0]
    last_tier_fee = SERVICE_FEE_TIERS[-1][1]
    extra_km = distance_km - last_tier_km
    extra_brackets = math.ceil(extra_km / BRACKET_SIZE_KM)
    return last_tier_fee + (FEE_PER_EXTRA_BRACKET * extra_brackets)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate straight-line distance between two GPS points (in km).
    Used as a fast fallback when ORS API is unavailable.
    """
    R = 6371  # Earth's radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_driving_distance(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> Tuple[float, Optional[float]]:
    """
    Get driving distance (km) and duration (minutes) between two points
    using the OpenRouteService Directions API.
    
    Returns (distance_km, duration_minutes).
    Falls back to haversine * 1.3 if ORS API is unreachable.
    """
    try:
        import httpx
        from config import settings

        api_key = settings.ORS_API_KEY
        if not api_key:
            raise ValueError("ORS_API_KEY not configured")

        # ORS expects coordinates as [longitude, latitude]
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "coordinates": [
                [origin_lng, origin_lat],
                [dest_lng, dest_lat],
            ]
        }

        resp = httpx.post(url, json=body, headers=headers, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()

        route = data["routes"][0]["summary"]
        distance_km = route["distance"] / 1000  # meters -> km
        duration_min = route["duration"] / 60    # seconds -> minutes

        logger.info(
            f"ORS distance: {distance_km:.2f} km, duration: {duration_min:.1f} min "
            f"({origin_lat},{origin_lng} -> {dest_lat},{dest_lng})"
        )
        return distance_km, duration_min

    except Exception as e:
        logger.warning(f"ORS API failed, falling back to haversine: {e}")
        straight = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        # Multiply by 1.3 to approximate road distance
        approx = straight * 1.3
        logger.info(f"Haversine fallback: {straight:.2f} km straight, {approx:.2f} km approx road")
        return approx, None


def compute_fee_between(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Convenience: compute both distance and fee in one call.
    Returns dict with distance_km, duration_minutes, service_fee, fee_source.
    """
    distance_km, duration_min = get_driving_distance(
        origin_lat, origin_lng, dest_lat, dest_lng
    )
    fee = calculate_service_fee(distance_km)

    return {
        "distance_km": round(distance_km, 2),
        "duration_minutes": round(duration_min, 1) if duration_min else None,
        "service_fee": float(fee),
        "fee_source": "ors" if duration_min is not None else "haversine_fallback",
    }
