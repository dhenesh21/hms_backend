from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class VehicleType(str, enum.Enum):
    BASIC_LIFE_SUPPORT = "basic_life_support"
    ADVANCED_LIFE_SUPPORT = "advanced_life_support"
    PATIENT_TRANSPORT = "patient_transport"
    NEONATAL = "neonatal"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class TripType(str, enum.Enum):
    EMERGENCY_PICKUP = "emergency_pickup"
    HOSPITAL_TRANSFER = "hospital_transfer"
    DISCHARGE_TRANSPORT = "discharge_transport"
    OTHER = "other"


class TripStatus(str, enum.Enum):
    REQUESTED = "requested"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AmbulanceVehicle(Base):
    __tablename__ = "ambulance_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(30), unique=True, index=True, nullable=False)
    vehicle_type = Column(Enum(VehicleType), default=VehicleType.BASIC_LIFE_SUPPORT)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.AVAILABLE)

    make_model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    equipment_notes = Column(Text, nullable=True)

    # GPS - last known position, updated via a dedicated endpoint.
    # This is a placeholder for real hardware/telematics integration.
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    location_updated_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trips = relationship("AmbulanceTrip", back_populates="vehicle")
    fuel_logs = relationship("AmbulanceFuelLog", back_populates="vehicle")
    maintenance_logs = relationship("AmbulanceMaintenanceLog", back_populates="vehicle")


class AmbulanceDriver(Base):
    __tablename__ = "ambulance_drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # optional link to staff account
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trips = relationship("AmbulanceTrip", back_populates="driver")


class AmbulanceTrip(Base):
    __tablename__ = "ambulance_trips"

    id = Column(Integer, primary_key=True, index=True)
    trip_number = Column(String(20), unique=True, index=True, nullable=False)

    vehicle_id = Column(Integer, ForeignKey("ambulance_vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("ambulance_drivers.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # may be unknown at request time
    er_visit_id = Column(Integer, ForeignKey("er_visits.id"), nullable=True)  # links to Emergency module

    trip_type = Column(Enum(TripType), default=TripType.EMERGENCY_PICKUP)
    status = Column(Enum(TripStatus), default=TripStatus.REQUESTED)

    pickup_location = Column(String(300), nullable=False)
    drop_location = Column(String(300), nullable=True)
    caller_name = Column(String(200), nullable=True)
    caller_phone = Column(String(20), nullable=True)

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    distance_km = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("AmbulanceVehicle", back_populates="trips")
    driver = relationship("AmbulanceDriver", back_populates="trips")


class AmbulanceFuelLog(Base):
    __tablename__ = "ambulance_fuel_logs"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("ambulance_vehicles.id"), nullable=False)
    filled_at = Column(DateTime(timezone=True), server_default=func.now())
    liters = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    odometer_reading = Column(Integer, nullable=True)
    filled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("AmbulanceVehicle", back_populates="fuel_logs")


class AmbulanceMaintenanceLog(Base):
    __tablename__ = "ambulance_maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("ambulance_vehicles.id"), nullable=False)
    maintenance_date = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=False)
    cost = Column(Float, nullable=True)
    next_due_date = Column(DateTime(timezone=True), nullable=True)
    performed_by = Column(String(200), nullable=True)  # workshop/vendor name
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    vehicle = relationship("AmbulanceVehicle", back_populates="maintenance_logs")
