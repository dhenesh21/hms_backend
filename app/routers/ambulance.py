from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.ambulance import (
    AmbulanceVehicle,
    AmbulanceDriver,
    AmbulanceTrip,
    AmbulanceFuelLog,
    AmbulanceMaintenanceLog,
    VehicleStatus,
    TripStatus,
)
from app.models.user import User
from app.schemas.ambulance import (
    VehicleCreate,
    VehicleUpdate,
    VehicleLocationUpdate,
    VehicleResponse,
    DriverCreate,
    DriverResponse,
    TripCreate,
    TripUpdate,
    TripResponse,
    FuelLogCreate,
    FuelLogResponse,
    MaintenanceLogCreate,
    MaintenanceLogResponse,
)

router = APIRouter(prefix="/ambulance", tags=["Ambulance"])


# ── VEHICLES ─────────────────────────────────────────────

@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    data: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.vehicle_number == data.vehicle_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="A vehicle with this number already exists")
    vehicle = AmbulanceVehicle(**data.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    status: Optional[VehicleStatus] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AmbulanceVehicle)
    if status:
        q = q.filter(AmbulanceVehicle.status == status)
    if active_only:
        q = q.filter(AmbulanceVehicle.is_active == True)  # noqa: E712
    return q.order_by(AmbulanceVehicle.vehicle_number).all()


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.put("/vehicles/{vehicle_id}/location", response_model=VehicleResponse)
async def update_vehicle_location(
    vehicle_id: int,
    data: VehicleLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GPS location update - roadmap's 'GPS' item. Placeholder for a real
    telematics/hardware integration; any tracker device can call this."""
    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    vehicle.current_latitude = data.latitude
    vehicle.current_longitude = data.longitude
    vehicle.location_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── DRIVERS ─────────────────────────────────────────────

@router.post("/drivers", response_model=DriverResponse, status_code=201)
async def create_driver(
    data: DriverCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(AmbulanceDriver).filter(AmbulanceDriver.license_number == data.license_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="A driver with this license number already exists")
    driver = AmbulanceDriver(**data.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/drivers", response_model=list[DriverResponse])
async def list_drivers(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AmbulanceDriver)
    if active_only:
        q = q.filter(AmbulanceDriver.is_active == True)  # noqa: E712
    return q.order_by(AmbulanceDriver.name).all()


# ── TRIPS ─────────────────────────────────────────────

@router.post("/trips", response_model=TripResponse, status_code=201)
async def request_trip(
    data: TripCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status != VehicleStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail=f"Vehicle is not available (status: {vehicle.status.value})")

    trip_data = data.model_dump()
    trip_data["requested_by"] = current_user.id

    attempt_base = next_sequence_number(db, AmbulanceTrip)
    trip = None
    last_error = None
    for i in range(MAX_RETRIES):
        trip_data["trip_number"] = f"AMB{attempt_base + i:06d}"
        trip = AmbulanceTrip(**trip_data)
        db.add(trip)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            trip = None
    if last_error:
        raise last_error

    vehicle.status = VehicleStatus.ON_TRIP
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/trips", response_model=list[TripResponse])
async def list_trips(
    status: Optional[TripStatus] = Query(None),
    vehicle_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AmbulanceTrip)
    if status:
        q = q.filter(AmbulanceTrip.status == status)
    if vehicle_id:
        q = q.filter(AmbulanceTrip.vehicle_id == vehicle_id)
    return q.order_by(AmbulanceTrip.requested_at.desc()).limit(limit).all()


@router.get("/trips/active", response_model=list[TripResponse])
async def active_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(AmbulanceTrip)
        .filter(AmbulanceTrip.status.in_([TripStatus.REQUESTED, TripStatus.DISPATCHED, TripStatus.IN_PROGRESS]))
        .order_by(AmbulanceTrip.requested_at.asc())
        .all()
    )


@router.put("/trips/{trip_id}/dispatch", response_model=TripResponse)
async def dispatch_trip(
    trip_id: int,
    data: TripUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(AmbulanceTrip).filter(AmbulanceTrip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != TripStatus.REQUESTED:
        raise HTTPException(status_code=400, detail=f"Cannot dispatch a trip with status '{trip.status.value}'")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(trip, field, value)
    trip.status = TripStatus.DISPATCHED
    trip.dispatched_at = datetime.utcnow()
    db.commit()
    db.refresh(trip)
    return trip


@router.put("/trips/{trip_id}/complete", response_model=TripResponse)
async def complete_trip(
    trip_id: int,
    data: TripUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(AmbulanceTrip).filter(AmbulanceTrip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status not in (TripStatus.DISPATCHED, TripStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail=f"Cannot complete a trip with status '{trip.status.value}'")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(trip, field, value)
    trip.status = TripStatus.COMPLETED
    trip.completed_at = datetime.utcnow()

    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == trip.vehicle_id).first()
    if vehicle:
        vehicle.status = VehicleStatus.AVAILABLE

    db.commit()
    db.refresh(trip)
    return trip


@router.put("/trips/{trip_id}/cancel", response_model=TripResponse)
async def cancel_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(AmbulanceTrip).filter(AmbulanceTrip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a trip with status '{trip.status.value}'")

    trip.status = TripStatus.CANCELLED

    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == trip.vehicle_id).first()
    if vehicle and vehicle.status == VehicleStatus.ON_TRIP:
        vehicle.status = VehicleStatus.AVAILABLE

    db.commit()
    db.refresh(trip)
    return trip


# ── FUEL & MAINTENANCE ─────────────────────────────────────────────

@router.post("/fuel-logs", response_model=FuelLogResponse, status_code=201)
async def add_fuel_log(
    data: FuelLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    log = AmbulanceFuelLog(**data.model_dump(), filled_by=current_user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/fuel-logs", response_model=list[FuelLogResponse])
async def list_fuel_logs(
    vehicle_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AmbulanceFuelLog)
    if vehicle_id:
        q = q.filter(AmbulanceFuelLog.vehicle_id == vehicle_id)
    return q.order_by(AmbulanceFuelLog.filled_at.desc()).all()


@router.post("/maintenance-logs", response_model=MaintenanceLogResponse, status_code=201)
async def add_maintenance_log(
    data: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    log = AmbulanceMaintenanceLog(**data.model_dump(), logged_by=current_user.id)
    db.add(log)
    vehicle.status = VehicleStatus.MAINTENANCE
    db.commit()
    db.refresh(log)
    return log


@router.get("/maintenance-logs", response_model=list[MaintenanceLogResponse])
async def list_maintenance_logs(
    vehicle_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AmbulanceMaintenanceLog)
    if vehicle_id:
        q = q.filter(AmbulanceMaintenanceLog.vehicle_id == vehicle_id)
    return q.order_by(AmbulanceMaintenanceLog.maintenance_date.desc()).all()


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def ambulance_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_vehicles = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.is_active == True).count()  # noqa: E712
    available = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.status == VehicleStatus.AVAILABLE).count()
    on_trip = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.status == VehicleStatus.ON_TRIP).count()
    in_maintenance = db.query(AmbulanceVehicle).filter(AmbulanceVehicle.status == VehicleStatus.MAINTENANCE).count()
    trips_today = db.query(AmbulanceTrip).filter(AmbulanceTrip.requested_at >= today_start).count()
    active_trips_count = (
        db.query(AmbulanceTrip)
        .filter(AmbulanceTrip.status.in_([TripStatus.REQUESTED, TripStatus.DISPATCHED, TripStatus.IN_PROGRESS]))
        .count()
    )

    return {
        "total_vehicles": total_vehicles,
        "available": available,
        "on_trip": on_trip,
        "in_maintenance": in_maintenance,
        "trips_today": trips_today,
        "active_trips": active_trips_count,
    }
