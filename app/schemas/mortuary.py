from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.mortuary import DeathSource, BodyStatus


class MortuaryRecordCreate(BaseModel):
    patient_id: int
    death_source: DeathSource = DeathSource.IPD
    ipd_admission_id: Optional[int] = None
    er_visit_id: Optional[int] = None
    cause_of_death: Optional[str] = None
    certified_by: Optional[int] = None
    is_mlc: bool = False
    storage_unit: Optional[str] = None
    postmortem_required: bool = False
    notes: Optional[str] = None


class MortuaryRecordUpdate(BaseModel):
    cause_of_death: Optional[str] = None
    storage_unit: Optional[str] = None
    postmortem_required: Optional[bool] = None
    notes: Optional[str] = None


class PostmortemUpdate(BaseModel):
    postmortem_doctor: str
    postmortem_findings: Optional[str] = None


class ReleaseRequest(BaseModel):
    released_to: str
    released_relation: Optional[str] = None


class CertificateIssueRequest(BaseModel):
    death_certificate_number: str


class MortuaryRecordResponse(BaseModel):
    id: int
    mortuary_number: str
    patient_id: int
    death_source: DeathSource
    ipd_admission_id: Optional[int]
    er_visit_id: Optional[int]
    date_of_death: datetime
    cause_of_death: Optional[str]
    certified_by: Optional[int]
    is_mlc: bool
    body_status: BodyStatus
    storage_unit: Optional[str]
    stored_at: datetime
    postmortem_required: bool
    postmortem_done: bool
    postmortem_date: Optional[datetime]
    postmortem_doctor: Optional[str]
    postmortem_findings: Optional[str]
    released_to: Optional[str]
    released_relation: Optional[str]
    release_date: Optional[datetime]
    death_certificate_number: Optional[str]
    death_certificate_issued: bool
    notes: Optional[str]

    class Config:
        from_attributes = True
