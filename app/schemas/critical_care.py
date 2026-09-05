from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.critical_care import CriticalCareUnit, CodeStatus


class CriticalCareAdmissionCreate(BaseModel):
    ipd_admission_id: int
    unit_type: CriticalCareUnit
    admission_reason: str
    apache_ii_score: Optional[int] = None
    code_status: CodeStatus = CodeStatus.FULL_CODE
    on_ventilator: bool = False
    central_line: bool = False
    central_line_site: Optional[str] = None
    urinary_catheter: bool = False
    arterial_line: bool = False


class CriticalCareAdmissionUpdate(BaseModel):
    code_status: Optional[CodeStatus] = None
    on_ventilator: Optional[bool] = None
    central_line: Optional[bool] = None
    central_line_site: Optional[str] = None
    urinary_catheter: Optional[bool] = None
    arterial_line: Optional[bool] = None
    apache_ii_score: Optional[int] = None


class StepDownRequest(BaseModel):
    step_down_notes: Optional[str] = None


class CriticalCareAdmissionResponse(BaseModel):
    id: int
    ipd_admission_id: int
    unit_type: CriticalCareUnit
    admission_reason: str
    apache_ii_score: Optional[int]
    code_status: CodeStatus
    on_ventilator: bool
    central_line: bool
    central_line_site: Optional[str]
    urinary_catheter: bool
    arterial_line: bool
    is_active: bool
    admitted_at: datetime
    stepped_down_at: Optional[datetime]
    step_down_notes: Optional[str]

    class Config:
        from_attributes = True


class RoundCreate(BaseModel):
    heart_rate: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    temperature: Optional[float] = None

    ventilator_mode: Optional[str] = None
    fio2_percent: Optional[float] = None
    peep: Optional[float] = None
    tidal_volume_ml: Optional[float] = None

    inotropes: Optional[str] = None
    sedation_score: Optional[int] = None
    gcs_score: Optional[int] = None
    urine_output_ml: Optional[int] = None
    notes: Optional[str] = None


class RoundResponse(RoundCreate):
    id: int
    critical_care_admission_id: int
    recorded_at: datetime
    recorded_by: Optional[int]

    class Config:
        from_attributes = True


class CriticalCareAdmissionDetailResponse(CriticalCareAdmissionResponse):
    rounds: list[RoundResponse] = []
