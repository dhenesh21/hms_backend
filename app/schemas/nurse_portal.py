from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date


class WardPatientResponse(BaseModel):
    admission_id: int
    patient_id: int
    bed_id: Optional[int]
    admission_date: datetime
    status: str

    class Config:
        from_attributes = True


class DueMedicationResponse(BaseModel):
    administration_id: int
    mar_id: int
    patient_id: int
    drug_name: str
    dose: str
    route: str
    scheduled_datetime: datetime
    status: str

    class Config:
        from_attributes = True


class GiveMedicationRequest(BaseModel):
    dose_given: Optional[str] = None
    remarks: Optional[str] = None


class MarkNotGivenRequest(BaseModel):
    reason_not_given: str
    status: str = "held"   # held, missed, refused


class LatestHandoverResponse(BaseModel):
    id: int
    ward_id: Optional[int]
    shift_date: date
    from_shift: str
    to_shift: str
    total_patients: int
    critical_patients: int
    general_notes: Optional[str]
    pending_tasks: Any
    critical_alerts: Any

    class Config:
        from_attributes = True


class NursingCarePlanResponse(BaseModel):
    id: int
    patient_id: int
    problem_statement: str
    goal: str
    status: str
    priority: str

    class Config:
        from_attributes = True


class NursingNoteCreate(BaseModel):
    admission_id: int
    note: str
    note_type: str = "general"
    shift: Optional[str] = None


class NursingNoteResponse(BaseModel):
    id: int
    admission_id: int
    note: str
    note_type: str
    shift: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
