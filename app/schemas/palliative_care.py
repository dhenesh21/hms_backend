from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.models.palliative_care import CareSetting


class PalliativePlanCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    primary_doctor_id: int
    primary_diagnosis: str
    care_setting: CareSetting = CareSetting.INPATIENT
    goals_of_care: Optional[str] = None
    code_status: Optional[str] = None
    primary_caregiver_name: Optional[str] = None
    primary_caregiver_contact: Optional[str] = None
    psychosocial_support_needed: bool = False
    spiritual_support_needed: bool = False


class PalliativePlanClose(BaseModel):
    closure_reason: str


class PalliativePlanResponse(BaseModel):
    id: int
    patient_id: int
    primary_diagnosis: str
    care_setting: CareSetting
    goals_of_care: Optional[str]
    is_active: bool
    started_at: datetime
    closed_at: Optional[datetime]
    closure_reason: Optional[str]

    class Config:
        from_attributes = True


class SymptomAssessmentCreate(BaseModel):
    care_plan_id: int
    symptom_scores: dict
    interventions_given: Optional[str] = None
    family_meeting_held: bool = False
    notes: Optional[str] = None


class SymptomAssessmentResponse(BaseModel):
    id: int
    care_plan_id: int
    assessed_at: datetime
    symptom_scores: Any
    family_meeting_held: bool

    class Config:
        from_attributes = True
