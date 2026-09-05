from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.infection_control import InfectionIncident, IsolationPrecaution, InfectionStatus, InfectionSource
from app.models.patient import Patient
from app.models.user import User
from app.schemas.infection_control import (
    InfectionIncidentCreate,
    InfectionIncidentUpdate,
    InfectionIncidentResponse,
    IsolationPrecautionCreate,
    IsolationPrecautionResponse,
)

router = APIRouter(prefix="/infection-control", tags=["Infection Control"])


# ── INFECTION INCIDENTS ─────────────────────────────────────────────

@router.post("/incidents", response_model=InfectionIncidentResponse, status_code=201)
async def report_incident(
    data: InfectionIncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    incident_data = data.model_dump()
    incident_data["reported_by"] = current_user.id

    attempt_base = next_sequence_number(db, InfectionIncident)
    incident = None
    last_error = None
    for i in range(MAX_RETRIES):
        incident_data["incident_number"] = f"INF{attempt_base + i:06d}"
        incident = InfectionIncident(**incident_data)
        db.add(incident)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            incident = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(incident)
    return incident


@router.get("/incidents", response_model=list[InfectionIncidentResponse])
async def list_incidents(
    status: Optional[InfectionStatus] = Query(None),
    source: Optional[InfectionSource] = Query(None),
    ward_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InfectionIncident)
    if status:
        q = q.filter(InfectionIncident.status == status)
    if source:
        q = q.filter(InfectionIncident.source == source)
    if ward_id:
        q = q.filter(InfectionIncident.ward_id == ward_id)
    return q.order_by(InfectionIncident.date_identified.desc()).limit(limit).all()


@router.get("/incidents/{incident_id}", response_model=InfectionIncidentResponse)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(InfectionIncident).filter(InfectionIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Infection incident not found")
    return incident


@router.put("/incidents/{incident_id}", response_model=InfectionIncidentResponse)
async def update_incident(
    incident_id: int,
    data: InfectionIncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(InfectionIncident).filter(InfectionIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Infection incident not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)

    if data.status == InfectionStatus.RESOLVED:
        incident.resolved_date = datetime.utcnow()

    db.commit()
    db.refresh(incident)
    return incident


# ── ISOLATION PRECAUTIONS ─────────────────────────────────────────────

@router.post("/isolation", response_model=IsolationPrecautionResponse, status_code=201)
async def start_isolation(
    data: IsolationPrecautionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing = (
        db.query(IsolationPrecaution)
        .filter(IsolationPrecaution.patient_id == data.patient_id, IsolationPrecaution.is_active == True)  # noqa: E712
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Patient already has an active isolation precaution")

    precaution = IsolationPrecaution(**data.model_dump(), started_by=current_user.id)
    db.add(precaution)
    db.commit()
    db.refresh(precaution)
    return precaution


@router.get("/isolation", response_model=list[IsolationPrecautionResponse])
async def list_isolation_precautions(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(IsolationPrecaution)
    if active_only:
        q = q.filter(IsolationPrecaution.is_active == True)  # noqa: E712
    return q.order_by(IsolationPrecaution.started_at.desc()).all()


@router.put("/isolation/{precaution_id}/end", response_model=IsolationPrecautionResponse)
async def end_isolation(
    precaution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    precaution = db.query(IsolationPrecaution).filter(IsolationPrecaution.id == precaution_id).first()
    if not precaution:
        raise HTTPException(status_code=404, detail="Isolation precaution not found")
    if not precaution.is_active:
        raise HTTPException(status_code=400, detail="This isolation precaution has already ended")

    precaution.is_active = False
    precaution.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(precaution)
    return precaution


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def infection_control_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    active_isolations = db.query(IsolationPrecaution).filter(IsolationPrecaution.is_active == True).count()  # noqa: E712
    incidents_this_month = (
        db.query(InfectionIncident).filter(InfectionIncident.date_identified >= month_start).count()
    )
    hospital_acquired_this_month = (
        db.query(InfectionIncident)
        .filter(
            InfectionIncident.date_identified >= month_start,
            InfectionIncident.source == InfectionSource.HOSPITAL_ACQUIRED,
        )
        .count()
    )
    under_investigation = (
        db.query(InfectionIncident).filter(InfectionIncident.status == InfectionStatus.UNDER_INVESTIGATION).count()
    )

    return {
        "active_isolations": active_isolations,
        "incidents_this_month": incidents_this_month,
        "hospital_acquired_this_month": hospital_acquired_this_month,
        "under_investigation": under_investigation,
    }
