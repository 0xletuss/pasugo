"""
models/location.py - User Location Tracking Model
Handles real-time location data for customers and riders
"""

from datetime import datetime
from typing import Optional, List, Dict
from decimal import Decimal


class UserLocation:
    """
    Represents a user's location record
    Stores real-time coordinates, accuracy, and location data
    """

    def __init__(
        self,
        location_id: Optional[int] = None,
        user_id: int = None,
        request_id: Optional[int] = None,
        latitude: Decimal = None,
        longitude: Decimal = None,
        accuracy: Optional[int] = None,
        address: Optional[str] = None,
        map_style_preference: str = "street",
        created_at: Optional[datetime] = None,
    ):
        self.location_id = location_id
        self.user_id = user_id
        self.request_id = request_id
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy  # GPS accuracy in meters
        self.address = address
        self.map_style_preference = map_style_preference
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_row(row: tuple) -> "UserLocation":
        """
        Create UserLocation instance from database row
        
        Args:
            row: Database query result row
            
        Returns:
            UserLocation instance
        """
        return UserLocation(
            location_id=row[0],
            user_id=row[1],
            request_id=row[2],
            latitude=row[3],
            longitude=row[4],
            accuracy=row[5],
            address=row[6],
            map_style_preference=row[7],
            created_at=row[8],
        )

    def to_dict(self) -> Dict:
        """
        Convert location to dictionary
        
        Returns:
            Dictionary representation of location
        """
        return {
            "location_id": self.location_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy": self.accuracy,
            "address": self.address,
            "map_style_preference": self.map_style_preference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_dict_with_rider_info(self, rider_info: Dict = None) -> Dict:
        """
        Convert to dictionary with rider additional information
        
        Args:
            rider_info: Dictionary with rider details (name, rating, vehicle, etc)
            
        Returns:
            Dictionary with location and rider info combined
        """
        data = self.to_dict()
        if rider_info:
            data.update(rider_info)
        return data

    def validate(self) -> bool:
        """
        Validate location data
        
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If critical data is missing or invalid
        """
        if not self.user_id:
            raise ValueError("user_id is required")

        # Validate latitude (-90 to 90)
        if self.latitude is None:
            raise ValueError("latitude is required")
        lat = float(self.latitude)
        if lat < -90 or lat > 90:
            raise ValueError("latitude must be between -90 and 90")

        # Validate longitude (-180 to 180)
        if self.longitude is None:
            raise ValueError("longitude is required")
        lng = float(self.longitude)
        if lng < -180 or lng > 180:
            raise ValueError("longitude must be between -180 and 180")

        # Validate accuracy if provided
        if self.accuracy is not None and self.accuracy < 0:
            raise ValueError("accuracy must be positive")

        return True

    def __repr__(self) -> str:
        return (
            f"<UserLocation(user_id={self.user_id}, "
            f"lat={self.latitude}, lng={self.longitude}, "
            f"accuracy={self.accuracy}m)>"
        )


class AvailableRider:
    """
    Represents an available rider with location info
    Combined data from riders, users, and user_locations tables
    """

    def __init__(
        self,
        rider_id: int,
        user_id: int,
        full_name: str,
        phone_number: str,
        vehicle_type: str,
        license_plate: str,
        availability_status: str,
        rating: Decimal,
        total_tasks_completed: int,
        latitude: Decimal,
        longitude: Decimal,
        accuracy: Optional[int] = None,
        address: Optional[str] = None,
        distance_km: Optional[Decimal] = None,
        last_location_update: Optional[datetime] = None,
    ):
        self.rider_id = rider_id
        self.user_id = user_id
        self.full_name = full_name
        self.phone_number = phone_number
        self.vehicle_type = vehicle_type
        self.license_plate = license_plate
        self.availability_status = availability_status
        self.rating = rating
        self.total_tasks_completed = total_tasks_completed
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.address = address
        self.distance_km = distance_km
        self.last_location_update = last_location_update

    @staticmethod
    def from_db_row(row: tuple) -> "AvailableRider":
        """
        Create AvailableRider instance from database row
        
        Args:
            row: Database query result row
            
        Returns:
            AvailableRider instance
        """
        return AvailableRider(
            rider_id=row[0],
            user_id=row[1],
            full_name=row[2],
            phone_number=row[3],
            vehicle_type=row[4],
            license_plate=row[5],
            availability_status=row[6],
            rating=row[7],
            total_tasks_completed=row[8],
            latitude=row[9],
            longitude=row[10],
            accuracy=row[11],
            address=row[12],
            distance_km=row[13],
            last_location_update=row[14],
        )

    def to_dict(self) -> Dict:
        """
        Convert available rider to dictionary for API response
        
        Returns:
            Dictionary representation
        """
        return {
            "rider_id": self.rider_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "phone_number": self.phone_number,
            "vehicle_type": self.vehicle_type,
            "license_plate": self.license_plate,
            "availability_status": self.availability_status,
            "rating": float(self.rating) if self.rating else 0.0,
            "total_tasks_completed": self.total_tasks_completed,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy": self.accuracy,
            "address": self.address,
            "distance_km": float(self.distance_km) if self.distance_km else None,
            "last_location_update": (
                self.last_location_update.isoformat()
                if self.last_location_update
                else None
            ),
        }

    def is_available(self) -> bool:
        """
        Check if rider is available for new requests
        
        Returns:
            True if status is 'available', False otherwise
        """
        return self.availability_status == "available"

    def is_busy(self) -> bool:
        """
        Check if rider is currently busy
        
        Returns:
            True if status is 'busy', False otherwise
        """
        return self.availability_status == "busy"

    def __repr__(self) -> str:
        return (
            f"<AvailableRider(name={self.full_name}, "
            f"vehicle={self.vehicle_type}, "
            f"distance={self.distance_km}km, "
            f"rating={self.rating})>"
        )


class LocationHistory:
    """
    Represents a record in user's location history
    Used for analytics and tracking
    """

    def __init__(
        self,
        history_id: Optional[int] = None,
        user_id: int = None,
        latitude: Decimal = None,
        longitude: Decimal = None,
        accuracy: Optional[int] = None,
        address: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.history_id = history_id
        self.user_id = user_id
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.address = address
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "history_id": self.history_id,
            "user_id": self.user_id,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy": self.accuracy,
            "address": self.address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self) -> str:
        return (
            f"<LocationHistory(user_id={self.user_id}, "
            f"lat={self.latitude}, lng={self.longitude})>"
        )