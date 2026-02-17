# routes/addresses.py
# Saved addresses CRUD for customers

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from models.user import User
from utils.dependencies import get_current_active_user

router = APIRouter(prefix="/addresses", tags=["Addresses"])


# ===== SCHEMAS =====

class AddressCreate(BaseModel):
    label: str  # e.g. "Home", "Work", "Mom's House"
    address_text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: Optional[bool] = None


# ===== ENDPOINTS =====

@router.get("/")
def get_my_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all saved addresses for the current user"""
    rows = db.execute(
        text("""
            SELECT address_id, label, address_text, latitude, longitude, is_default, created_at
            FROM saved_addresses
            WHERE user_id = :uid
            ORDER BY is_default DESC, created_at DESC
        """),
        {"uid": current_user.user_id}
    ).fetchall()

    addresses = []
    for r in rows:
        addresses.append({
            "address_id": r[0],
            "label": r[1],
            "address_text": r[2],
            "latitude": float(r[3]) if r[3] else None,
            "longitude": float(r[4]) if r[4] else None,
            "is_default": bool(r[5]),
            "created_at": r[6].isoformat() if r[6] else None
        })

    return {"success": True, "data": addresses}


@router.post("/")
def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new saved address"""
    # Limit to 10 addresses
    count = db.execute(
        text("SELECT COUNT(*) FROM saved_addresses WHERE user_id = :uid"),
        {"uid": current_user.user_id}
    ).scalar()

    if count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 saved addresses allowed")

    # If setting as default, unset others
    if address.is_default:
        db.execute(
            text("UPDATE saved_addresses SET is_default = 0 WHERE user_id = :uid"),
            {"uid": current_user.user_id}
        )

    now = datetime.utcnow()
    result = db.execute(
        text("""
            INSERT INTO saved_addresses (user_id, label, address_text, latitude, longitude, is_default, created_at)
            VALUES (:uid, :label, :address_text, :lat, :lng, :is_default, :now)
        """),
        {
            "uid": current_user.user_id,
            "label": address.label,
            "address_text": address.address_text,
            "lat": address.latitude,
            "lng": address.longitude,
            "is_default": address.is_default,
            "now": now
        }
    )
    db.commit()

    return {
        "success": True,
        "message": "Address saved",
        "data": {"address_id": result.lastrowid}
    }


@router.put("/{address_id}")
def update_address(
    address_id: int,
    address: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a saved address"""
    existing = db.execute(
        text("SELECT address_id FROM saved_addresses WHERE address_id = :aid AND user_id = :uid"),
        {"aid": address_id, "uid": current_user.user_id}
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")

    # If setting as default, unset others
    if address.is_default:
        db.execute(
            text("UPDATE saved_addresses SET is_default = 0 WHERE user_id = :uid"),
            {"uid": current_user.user_id}
        )

    updates = []
    params = {"aid": address_id, "uid": current_user.user_id}

    if address.label is not None:
        updates.append("label = :label")
        params["label"] = address.label
    if address.address_text is not None:
        updates.append("address_text = :address_text")
        params["address_text"] = address.address_text
    if address.latitude is not None:
        updates.append("latitude = :lat")
        params["lat"] = address.latitude
    if address.longitude is not None:
        updates.append("longitude = :lng")
        params["lng"] = address.longitude
    if address.is_default is not None:
        updates.append("is_default = :is_default")
        params["is_default"] = address.is_default

    if updates:
        db.execute(
            text(f"UPDATE saved_addresses SET {', '.join(updates)} WHERE address_id = :aid AND user_id = :uid"),
            params
        )
        db.commit()

    return {"success": True, "message": "Address updated"}


@router.delete("/{address_id}")
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a saved address"""
    existing = db.execute(
        text("SELECT address_id FROM saved_addresses WHERE address_id = :aid AND user_id = :uid"),
        {"aid": address_id, "uid": current_user.user_id}
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")

    db.execute(
        text("DELETE FROM saved_addresses WHERE address_id = :aid AND user_id = :uid"),
        {"aid": address_id, "uid": current_user.user_id}
    )
    db.commit()

    return {"success": True, "message": "Address deleted"}
