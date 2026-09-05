from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.security_incident import SecurityIncident, IncidentStatus, IncidentSeverity
from app.models.user import User
from app.schemas.security_incident import SecurityIncidentCreate, SecurityIncidentUpdate, SecurityIncidentResponse

router = APIRouter(prefix="/security-incidents", tags=["Security Incident Management"])


@router.post("", response_model=SecurityIncidentResponse, status_code=201)
async def report_incident(
    data: SecurityIncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident_data = data.model_dump()
    incident_data["reported_by"] = current_user.id

    attempt_base = next_sequence_number(db, SecurityIncident)
    incident = None
    last_error = None
    for i in range(MAX_RETRIES):
        incident_data["incident_number"] = f"SEC{attempt_base + i:06d}"
        incident = SecurityIncident(**incident_data)
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


@router.get("", response_model=list[SecurityIncidentResponse])
async def list_incidents(
    status: Optional[IncidentStatus] = Query(None),
    severity: Optional[IncidentSeverity] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(SecurityIncident)
    if status:
        q = q.filter(SecurityIncident.status == status)
    if severity:
        q = q.filter(SecurityIncident.severity == severity)
    return q.order_by(SecurityIncident.incident_datetime.desc()).limit(limit).all()


@router.get("/{incident_id}", response_model=SecurityIncidentResponse)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(SecurityIncident).filter(SecurityIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Security incident not found")
    return incident


@router.put("/{incident_id}", response_model=SecurityIncidentResponse)
async def update_incident(
    incident_id: int,
    data: SecurityIncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(SecurityIncident).filter(SecurityIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Security incident not found")
    if incident.status == IncidentStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot update a closed incident")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)

    if data.status == IncidentStatus.RESOLVED:
        incident.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)
    return incident


@router.get("/dashboard/stats")
async def security_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    open_incidents = (
        db.query(SecurityIncident)
        .filter(SecurityIncident.status.in_([IncidentStatus.REPORTED, IncidentStatus.UNDER_INVESTIGATION]))
        .count()
    )
    critical_open = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.status.in_([IncidentStatus.REPORTED, IncidentStatus.UNDER_INVESTIGATION]),
            SecurityIncident.severity == IncidentSeverity.CRITICAL,
        )
        .count()
    )
    incidents_this_month = db.query(SecurityIncident).filter(SecurityIncident.incident_datetime >= month_start).count()

    return {
        "open_incidents": open_incidents,
        "critical_open": critical_open,
        "incidents_this_month": incidents_this_month,
    }
