from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.emergency import TriageLevel, ERVisitStatus, ArrivalMode


class TriageCreate(BaseModel):
    triage_level: TriageLevel
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    glasgow_coma_scale: Optional[int] = None
    pain_score: Optional[int] = None
    notes: Optional[str] = None


class TriageResponse(TriageCreate):
    id: int
    er_visit_id: int
    triage_time: datetime
    triaged_by: Optional[int]

    class Config:
        from_attributes = True


class TreatmentCreate(BaseModel):
    treatment_given: str
    medication_given: Optional[str] = None
    procedure_performed: Optional[str] = None
    notes: Optional[str] = None


class TreatmentResponse(TreatmentCreate):
    id: int
    er_visit_id: int
    treatment_time: datetime
    given_by: Optional[int]

    class Config:
        from_attributes = True


class ERVisitCreate(BaseModel):
    patient_id: int
    arrival_mode: ArrivalMode = ArrivalMode.WALK_IN
    brought_by: Optional[str] = None
    chief_complaint: str

    is_mlc: bool = False
    mlc_number: Optional[str] = None
    is_trauma: bool = False
    incident_type: Optional[str] = None
    incident_datetime: Optional[datetime] = None
    police_informed: bool = False
    police_station: Optional[str] = None
    fir_number: Optional[str] = None

    attending_doctor_id: Optional[int] = None

    # Optional: record initial triage in the same call
    triage: Optional[TriageCreate] = None


class ERVisitUpdate(BaseModel):
    status: Optional[ERVisitStatus] = None
    attending_doctor_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    outcome_notes: Optional[str] = None
    is_mlc: Optional[bool] = None
    mlc_number: Optional[str] = None
    police_informed: Optional[bool] = None
    police_station: Optional[str] = None
    fir_number: Optional[str] = None


class ERVisitResponse(BaseModel):
    id: int
    er_number: str
    patient_id: int
    arrival_time: datetime
    arrival_mode: ArrivalMode
    brought_by: Optional[str]
    chief_complaint: str
    status: ERVisitStatus

    is_mlc: bool
    mlc_number: Optional[str]
    is_trauma: bool
    incident_type: Optional[str]
    incident_datetime: Optional[datetime]
    police_informed: bool
    police_station: Optional[str]
    fir_number: Optional[str]

    attending_doctor_id: Optional[int]
    ipd_admission_id: Optional[int]
    outcome_notes: Optional[str]
    discharge_time: Optional[datetime]

    created_at: datetime

    class Config:
        from_attributes = True


class ERVisitDetailResponse(ERVisitResponse):
    triage: Optional[TriageResponse] = None
    treatments: list[TreatmentResponse] = []
