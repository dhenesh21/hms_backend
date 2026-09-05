from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.recovery_room import RecoveryStatus


class RecoveryStayCreate(BaseModel):
    surgery_id: int
    patient_id: int
    aldrete_score: Optional[int] = None
    pain_score_on_arrival: Optional[int] = None
    nausea_vomiting: bool = False
    airway_patent: bool = True
    bleeding_at_site: bool = False


class RecoveryStayDischarge(BaseModel):
    discharge_destination: str
    discharge_notes: Optional[str] = None
    aldrete_score: Optional[int] = None


class RecoveryStayResponse(BaseModel):
    id: int
    surgery_id: int
    patient_id: int
    status: RecoveryStatus
    aldrete_score: Optional[int]
    admitted_at: datetime
    discharged_at: Optional[datetime]
    discharge_destination: Optional[str]

    class Config:
        from_attributes = True


class RecoveryObservationCreate(BaseModel):
    recovery_stay_id: int
    heart_rate: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[int] = None
    consciousness_level: Optional[str] = None
    pain_score: Optional[int] = None
    notes: Optional[str] = None


class RecoveryObservationResponse(BaseModel):
    id: int
    recovery_stay_id: int
    recorded_at: datetime
    heart_rate: Optional[int]
    spo2: Optional[float]
    pain_score: Optional[int]

    class Config:
        from_attributes = True
