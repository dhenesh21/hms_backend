from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date
from app.models.physiotherapy import RehabPlanStatus, SessionStatus


class PhysioPlanCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    referring_doctor_id: Optional[int] = None
    therapist_id: Optional[int] = None
    diagnosis: str
    goals: List[str] = []
    plan_details: Optional[str] = None
    frequency_per_week: int = 3
    total_sessions_planned: Optional[int] = None


class PhysioPlanResponse(BaseModel):
    id: int
    patient_id: int
    diagnosis: str
    goals: Any
    status: RehabPlanStatus
    frequency_per_week: int
    total_sessions_planned: Optional[int]
    started_on: date

    class Config:
        from_attributes = True


class PhysioSessionCreate(BaseModel):
    plan_id: int
    scheduled_at: datetime
    therapist_id: Optional[int] = None


class PhysioSessionComplete(BaseModel):
    activities_performed: str
    pain_score_before: Optional[int] = None
    pain_score_after: Optional[int] = None
    functional_improvement_notes: Optional[str] = None
    patient_tolerance: Optional[str] = None


class PhysioSessionResponse(BaseModel):
    id: int
    plan_id: int
    scheduled_at: datetime
    status: SessionStatus
    pain_score_before: Optional[int]
    pain_score_after: Optional[int]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
