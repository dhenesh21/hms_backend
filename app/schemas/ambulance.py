from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.ambulance import VehicleType, VehicleStatus, TripType, TripStatus


class VehicleCreate(BaseModel):
    vehicle_number: str
    vehicle_type: VehicleType = VehicleType.BASIC_LIFE_SUPPORT
    make_model: Optional[str] = None
    year: Optional[int] = None
    equipment_notes: Optional[str] = None


class VehicleUpdate(BaseModel):
    status: Optional[VehicleStatus] = None
    equipment_notes: Optional[str] = None
    is_active: Optional[bool] = None


class VehicleLocationUpdate(BaseModel):
    latitude: float
    longitude: float


class VehicleResponse(BaseModel):
    id: int
    vehicle_number: str
    vehicle_type: VehicleType
    status: VehicleStatus
    make_model: Optional[str]
    year: Optional[int]
    equipment_notes: Optional[str]
    current_latitude: Optional[float]
    current_longitude: Optional[float]
    location_updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class DriverCreate(BaseModel):
    name: str
    phone: str
    license_number: str
    user_id: Optional[int] = None


class DriverResponse(DriverCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class TripCreate(BaseModel):
    vehicle_id: int
    driver_id: Optional[int] = None
    patient_id: Optional[int] = None
    er_visit_id: Optional[int] = None
    trip_type: TripType = TripType.EMERGENCY_PICKUP
    pickup_location: str
    drop_location: Optional[str] = None
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    notes: Optional[str] = None


class TripUpdate(BaseModel):
    driver_id: Optional[int] = None
    drop_location: Optional[str] = None
    distance_km: Optional[float] = None
    notes: Optional[str] = None


class TripResponse(BaseModel):
    id: int
    trip_number: str
    vehicle_id: int
    driver_id: Optional[int]
    patient_id: Optional[int]
    er_visit_id: Optional[int]
    trip_type: TripType
    status: TripStatus
    pickup_location: str
    drop_location: Optional[str]
    caller_name: Optional[str]
    caller_phone: Optional[str]
    requested_at: datetime
    dispatched_at: Optional[datetime]
    completed_at: Optional[datetime]
    distance_km: Optional[float]
    notes: Optional[str]

    class Config:
        from_attributes = True


class FuelLogCreate(BaseModel):
    vehicle_id: int
    liters: float
    cost: float
    odometer_reading: Optional[int] = None
    notes: Optional[str] = None


class FuelLogResponse(FuelLogCreate):
    id: int
    filled_at: datetime
    filled_by: Optional[int]

    class Config:
        from_attributes = True


class MaintenanceLogCreate(BaseModel):
    vehicle_id: int
    description: str
    cost: Optional[float] = None
    next_due_date: Optional[datetime] = None
    performed_by: Optional[str] = None


class MaintenanceLogResponse(MaintenanceLogCreate):
    id: int
    maintenance_date: datetime
    logged_by: Optional[int]

    class Config:
        from_attributes = True
