from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.security_incident import IncidentType, IncidentSeverity, IncidentStatus


class SecurityIncidentCreate(BaseModel):
    incident_type: IncidentType = IncidentType.OTHER
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    location: str
    description: str
    persons_involved: Optional[str] = None
    police_informed: str = "no"
    police_report_number: Optional[str] = None


class SecurityIncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    investigated_by: Optional[str] = None
    investigation_notes: Optional[str] = None
    resolution: Optional[str] = None
    police_informed: Optional[str] = None
    police_report_number: Optional[str] = None


class SecurityIncidentResponse(BaseModel):
    id: int
    incident_number: str
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    location: str
    description: str
    persons_involved: Optional[str]
    incident_datetime: datetime
    police_informed: str
    police_report_number: Optional[str]
    investigated_by: Optional[str]
    investigation_notes: Optional[str]
    resolution: Optional[str]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
