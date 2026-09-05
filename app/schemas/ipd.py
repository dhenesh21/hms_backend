from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.ipd import WardType, BedStatus, AdmissionType, IPDStatus


# ── Ward & Bed ────────────────────────────────────────
class WardCreate(BaseModel):
    name: str
    ward_type: WardType
    floor: int = 1
    total_beds: int
    charge_per_day: float = 0.0


class WardResponse(BaseModel):
    id: int
    name: str
    ward_type: WardType
    floor: int
    total_beds: int
    available_beds: int
    charge_per_day: float
    is_active: bool

    class Config:
        from_attributes = True


class BedCreate(BaseModel):
    bed_number: str
    ward_id: int
    bed_type: str = "standard"


class BedResponse(BaseModel):
    id: int
    bed_number: str
    ward_id: int
    bed_type: str
    status: BedStatus
    is_active: bool

    class Config:
        from_attributes = True


# ── IPD Admission ─────────────────────────────────────
class IPDAdmissionCreate(BaseModel):
    patient_id: int
    bed_id: Optional[int] = None
    ward_id: Optional[int] = None
    admitting_doctor_id: int
    primary_doctor_id: Optional[int] = None
    expected_discharge_date: Optional[date] = None
    admission_type: AdmissionType = AdmissionType.ELECTIVE
    chief_complaint: Optional[str] = None
    diagnosis_at_admission: Optional[str] = None
    transferred_from: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    tpa_name: Optional[str] = None
    remarks: Optional[str] = None


class IPDAdmissionUpdate(BaseModel):
    bed_id: Optional[int] = None
    ward_id: Optional[int] = None
    primary_doctor_id: Optional[int] = None
    status: Optional[IPDStatus] = None
    expected_discharge_date: Optional[date] = None
    discharge_diagnosis: Optional[str] = None
    discharge_summary: Optional[str] = None
    discharge_instructions: Optional[str] = None
    condition_at_discharge: Optional[str] = None
    transferred_to: Optional[str] = None
    transfer_reason: Optional[str] = None


class IPDAdmissionResponse(BaseModel):
    id: int
    admission_number: str
    patient_id: int
    bed_id: Optional[int]
    ward_id: Optional[int]
    admitting_doctor_id: int
    primary_doctor_id: Optional[int]
    admission_date: datetime
    expected_discharge_date: Optional[date]
    discharge_date: Optional[datetime]
    admission_type: AdmissionType
    status: IPDStatus
    chief_complaint: Optional[str]
    diagnosis_at_admission: Optional[str]
    discharge_diagnosis: Optional[str]
    discharge_summary: Optional[str]
    insurance_provider: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Nursing Notes ─────────────────────────────────────
class NursingNoteCreate(BaseModel):
    admission_id: int
    note_type: str = "general"
    note: str
    shift: Optional[str] = None


class NursingNoteResponse(BaseModel):
    id: int
    admission_id: int
    nurse_id: int
    note_type: str
    note: str
    shift: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Daily Progress Notes ──────────────────────────────
class ProgressNoteCreate(BaseModel):
    admission_id: int
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None


class ProgressNoteResponse(BaseModel):
    id: int
    admission_id: int
    doctor_id: int
    note_date: date
    subjective: Optional[str]
    objective: Optional[str]
    assessment: Optional[str]
    plan: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Vital Chart ───────────────────────────────────────
class VitalChartCreate(BaseModel):
    admission_id: int
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    blood_sugar: Optional[float] = None
    urine_output_ml: Optional[int] = None
    pain_score: Optional[int] = None
    gcs_score: Optional[int] = None
    notes: Optional[str] = None


class VitalChartResponse(BaseModel):
    id: int
    admission_id: int
    recorded_by: Optional[int]
    recorded_at: datetime
    temperature: Optional[float]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    pulse_rate: Optional[int]
    respiratory_rate: Optional[int]
    oxygen_saturation: Optional[float]
    blood_sugar: Optional[float]
    urine_output_ml: Optional[int]
    pain_score: Optional[int]
    gcs_score: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True
