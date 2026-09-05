from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.infection_control import InfectionSource, InfectionStatus, PrecautionType


class InfectionIncidentCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    ward_id: Optional[int] = None
    infection_type: str
    source: InfectionSource = InfectionSource.UNKNOWN
    symptoms: Optional[str] = None
    lab_confirmation_id: Optional[int] = None


class InfectionIncidentUpdate(BaseModel):
    status: Optional[InfectionStatus] = None
    corrective_action: Optional[str] = None


class InfectionIncidentResponse(BaseModel):
    id: int
    incident_number: str
    patient_id: int
    ipd_admission_id: Optional[int]
    ward_id: Optional[int]
    infection_type: str
    source: InfectionSource
    status: InfectionStatus
    date_identified: datetime
    symptoms: Optional[str]
    lab_confirmation_id: Optional[int]
    corrective_action: Optional[str]
    resolved_date: Optional[datetime]

    class Config:
        from_attributes = True


class IsolationPrecautionCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    bed_id: Optional[int] = None
    infection_incident_id: Optional[int] = None
    precaution_type: PrecautionType = PrecautionType.STANDARD
    reason: Optional[str] = None


class IsolationPrecautionResponse(BaseModel):
    id: int
    patient_id: int
    ipd_admission_id: Optional[int]
    bed_id: Optional[int]
    infection_incident_id: Optional[int]
    precaution_type: PrecautionType
    reason: Optional[str]
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True
