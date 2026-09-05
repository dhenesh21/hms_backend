from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.mental_health import RiskLevel, MentalHealthPlanStatus


class PsychAssessmentCreate(BaseModel):
    patient_id: int
    psychiatrist_id: int
    source: Optional[str] = None
    source_id: Optional[int] = None
    presenting_complaint: str
    mental_status_exam: Optional[str] = None
    risk_self_harm: RiskLevel = RiskLevel.NONE
    risk_to_others: RiskLevel = RiskLevel.NONE
    provisional_diagnosis: Optional[str] = None
    icd_code: Optional[str] = None
    safety_plan_created: bool = False
    family_involved: bool = False


class PsychAssessmentResponse(BaseModel):
    id: int
    patient_id: int
    presenting_complaint: str
    risk_self_harm: RiskLevel
    risk_to_others: RiskLevel
    provisional_diagnosis: Optional[str]
    safety_plan_created: bool
    assessed_at: datetime

    class Config:
        from_attributes = True


class MHCarePlanCreate(BaseModel):
    patient_id: int
    assessment_id: Optional[int] = None
    psychiatrist_id: int
    diagnosis: str
    treatment_modalities: List[str] = []
    goals: List[str] = []


class MHCarePlanResponse(BaseModel):
    id: int
    patient_id: int
    diagnosis: str
    treatment_modalities: Any
    status: MentalHealthPlanStatus
    started_at: datetime

    class Config:
        from_attributes = True


class TherapySessionCreate(BaseModel):
    care_plan_id: int
    therapist_id: Optional[int] = None
    session_type: Optional[str] = None
    scheduled_at: datetime


class TherapySessionUpdate(BaseModel):
    attended: bool
    session_notes: Optional[str] = None
    risk_reassessed: Optional[RiskLevel] = None


class TherapySessionResponse(BaseModel):
    id: int
    care_plan_id: int
    session_type: Optional[str]
    scheduled_at: datetime
    attended: Optional[bool]
    risk_reassessed: Optional[RiskLevel]

    class Config:
        from_attributes = True
