from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.pain_management import PainType


class PainPlanCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    managing_doctor_id: int
    pain_type: PainType
    pain_location: Optional[str] = None
    baseline_pain_score: Optional[int] = None
    treatment_plan: Optional[str] = None
    target_pain_score: int = 3


class PainPlanResponse(BaseModel):
    id: int
    patient_id: int
    pain_type: PainType
    pain_location: Optional[str]
    baseline_pain_score: Optional[int]
    target_pain_score: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PainAssessmentCreate(BaseModel):
    plan_id: int
    pain_score: int
    pain_character: Optional[str] = None
    interventions_given: List[dict] = []
    response_after_intervention: Optional[str] = None
    side_effects_noted: Optional[str] = None
    notes: Optional[str] = None


class PainAssessmentResponse(BaseModel):
    id: int
    plan_id: int
    assessed_at: datetime
    pain_score: int
    pain_character: Optional[str]
    interventions_given: Any

    class Config:
        from_attributes = True
