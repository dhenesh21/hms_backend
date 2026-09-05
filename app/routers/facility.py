from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.facility import Equipment, EquipmentMaintenanceLog, FacilityServiceRequest, EquipmentStatus, ServiceRequestStatus
from app.models.user import User
from app.schemas.facility import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    MaintenanceLogCreate,
    MaintenanceLogResponse,
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceRequestResponse,
)

router = APIRouter(prefix="/facility", tags=["Facility & Equipment"])


# ── EQUIPMENT ─────────────────────────────────────────────

@router.post("/equipment", response_model=EquipmentResponse, status_code=201)
async def register_equipment(
    data: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Equipment).filter(Equipment.asset_code == data.asset_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="An equipment with this asset code already exists")
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


@router.get("/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    status: Optional[EquipmentStatus] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Equipment)
    if status:
        q = q.filter(Equipment.status == status)
    if department:
        q = q.filter(Equipment.department == department)
    return q.order_by(Equipment.name).all()


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return equipment


@router.post("/equipment/{equipment_id}/maintenance", response_model=MaintenanceLogResponse, status_code=201)
async def log_maintenance(
    equipment_id: int,
    data: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    log = EquipmentMaintenanceLog(**data.model_dump(), equipment_id=equipment_id, logged_by=current_user.id)
    db.add(log)
    # Maintenance being logged implies the equipment was under maintenance;
    # bring it back to operational once logged (corrective/preventive done).
    equipment.status = EquipmentStatus.OPERATIONAL
    db.commit()
    db.refresh(log)
    return log


@router.get("/equipment/{equipment_id}/maintenance", response_model=list[MaintenanceLogResponse])
async def list_maintenance_logs(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(EquipmentMaintenanceLog)
        .filter(EquipmentMaintenanceLog.equipment_id == equipment_id)
        .order_by(EquipmentMaintenanceLog.performed_at.desc())
        .all()
    )


# ── FACILITY SERVICE REQUESTS ─────────────────────────────────────────────

@router.post("/service-requests", response_model=ServiceRequestResponse, status_code=201)
async def create_service_request(
    data: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_data = data.model_dump()
    request_data["raised_by"] = current_user.id

    attempt_base = next_sequence_number(db, FacilityServiceRequest)
    request_obj = None
    last_error = None
    for i in range(MAX_RETRIES):
        request_data["request_number"] = f"FSR{attempt_base + i:06d}"
        request_obj = FacilityServiceRequest(**request_data)
        db.add(request_obj)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            request_obj = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(request_obj)
    return request_obj


@router.get("/service-requests", response_model=list[ServiceRequestResponse])
async def list_service_requests(
    status: Optional[ServiceRequestStatus] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(FacilityServiceRequest)
    if status:
        q = q.filter(FacilityServiceRequest.status == status)
    return q.order_by(FacilityServiceRequest.raised_at.desc()).limit(limit).all()


@router.put("/service-requests/{request_id}", response_model=ServiceRequestResponse)
async def update_service_request(
    request_id: int,
    data: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(FacilityServiceRequest).filter(FacilityServiceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Service request not found")
    if req.status == ServiceRequestStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot update a closed service request")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(req, field, value)

    if data.status == ServiceRequestStatus.RESOLVED:
        req.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(req)
    return req


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def facility_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_equipment = db.query(Equipment).count()
    under_maintenance = db.query(Equipment).filter(Equipment.status == EquipmentStatus.UNDER_MAINTENANCE).count()
    out_of_service = db.query(Equipment).filter(Equipment.status == EquipmentStatus.OUT_OF_SERVICE).count()
    open_requests = (
        db.query(FacilityServiceRequest)
        .filter(FacilityServiceRequest.status.in_([ServiceRequestStatus.OPEN, ServiceRequestStatus.IN_PROGRESS]))
        .count()
    )
    critical_requests = (
        db.query(FacilityServiceRequest)
        .filter(
            FacilityServiceRequest.status.in_([ServiceRequestStatus.OPEN, ServiceRequestStatus.IN_PROGRESS]),
            FacilityServiceRequest.priority == "critical",
        )
        .count()
    )

    return {
        "total_equipment": total_equipment,
        "under_maintenance": under_maintenance,
        "out_of_service": out_of_service,
        "open_requests": open_requests,
        "critical_requests": critical_requests,
    }
