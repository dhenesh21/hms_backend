from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.nursing import (MedicationFrequency, AdministrationStatus,
                                  AssessmentType, CarePlanStatus)


class MARCreate(BaseModel):
    ipd_admission_id: int
    patient_id: int
    drug_name: str
    generic_name: Optional[str] = None
    drug_id: Optional[int] = None
    dose: str
    route: str = "oral"
    frequency: MedicationFrequency
    scheduled_times: List[str] = []
    ordered_by: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    instructions: Optional[str] = None


class MARResponse(BaseModel):
    id: int
    ipd_admission_id: int
    patient_id: int
    drug_name: str
    generic_name: Optional[str]
    dose: str
    route: str
    frequency: MedicationFrequency
    scheduled_times: List[str]
    start_date: date
    end_date: Optional[date]
    instructions: Optional[str]
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class AdministrationRecord(BaseModel):
    mar_id: int
    scheduled_datetime: datetime
    status: AdministrationStatus
    dose_given: Optional[str] = None
    remarks: Optional[str] = None
    reason_not_given: Optional[str] = None


class AdministrationResponse(BaseModel):
    id: int
    mar_id: int
    scheduled_datetime: datetime
    administered_datetime: Optional[datetime]
    status: AdministrationStatus
    administered_by: Optional[int]
    dose_given: Optional[str]
    remarks: Optional[str]
    reason_not_given: Optional[str]
    class Config:
        from_attributes = True


class NursingAssessmentCreate(BaseModel):
    ipd_admission_id: int
    patient_id: int
    assessment_type: AssessmentType
    general_condition: Optional[str] = None
    consciousness: Optional[str] = None
    orientation: Optional[str] = None
    pain_score: Optional[int] = None
    pain_location: Optional[str] = None
    pain_character: Optional[str] = None
    pain_relieving_factors: Optional[str] = None
    fall_risk_score: Optional[int] = None
    fall_risk_level: Optional[str] = None
    braden_score: Optional[int] = None
    pressure_ulcer_risk: Optional[str] = None
    existing_wounds: Optional[str] = None
    nutritional_status: Optional[str] = None
    diet_type: Optional[str] = None
    allergies_noted: Optional[str] = None
    respiratory: Optional[str] = None
    cardiovascular: Optional[str] = None
    neurological: Optional[str] = None
    gastrointestinal: Optional[str] = None
    genitourinary: Optional[str] = None
    musculoskeletal: Optional[str] = None
    integumentary: Optional[str] = None
    iv_access: Optional[str] = None
    catheters: Optional[str] = None
    drains: Optional[str] = None
    oxygen_therapy: Optional[str] = None
    additional_notes: Optional[str] = None


class NursingAssessmentResponse(BaseModel):
    id: int
    ipd_admission_id: int
    patient_id: int
    assessment_type: AssessmentType
    assessment_date: datetime
    assessed_by: int
    general_condition: Optional[str]
    consciousness: Optional[str]
    pain_score: Optional[int]
    fall_risk_score: Optional[int]
    fall_risk_level: Optional[str]
    braden_score: Optional[int]
    pressure_ulcer_risk: Optional[str]
    nutritional_status: Optional[str]
    additional_notes: Optional[str]
    class Config:
        from_attributes = True


class CarePlanCreate(BaseModel):
    ipd_admission_id: int
    patient_id: int
    problem_statement: str
    nursing_diagnosis: Optional[str] = None
    goal: str
    interventions: List[str] = []
    expected_outcome: Optional[str] = None
    target_date: Optional[date] = None
    priority: str = "medium"


class CarePlanUpdate(BaseModel):
    status: Optional[CarePlanStatus] = None
    goal: Optional[str] = None
    interventions: Optional[List[str]] = None
    evaluation_notes: Optional[str] = None
    achieved_date: Optional[date] = None


class CareInterventionCreate(BaseModel):
    care_plan_id: int
    intervention: str
    outcome: Optional[str] = None
    patient_response: Optional[str] = None


class CarePlanResponse(BaseModel):
    id: int
    ipd_admission_id: int
    patient_id: int
    problem_statement: str
    nursing_diagnosis: Optional[str]
    goal: str
    interventions: List[str]
    expected_outcome: Optional[str]
    status: CarePlanStatus
    target_date: Optional[date]
    achieved_date: Optional[date]
    evaluation_notes: Optional[str]
    priority: str
    created_at: datetime
    class Config:
        from_attributes = True


class ShiftHandoverCreate(BaseModel):
    ward_id: Optional[int] = None
    shift_date: date
    from_shift: str
    to_shift: str
    total_patients: int = 0
    critical_patients: int = 0
    new_admissions: int = 0
    discharges: int = 0
    general_notes: Optional[str] = None
    pending_tasks: List[str] = []
    critical_alerts: List[str] = []
    equipment_issues: Optional[str] = None
    patient_summaries: List[dict] = []


class ShiftHandoverResponse(BaseModel):
    id: int
    ward_id: Optional[int]
    shift_date: date
    from_shift: str
    to_shift: str
    handover_by: int
    received_by: Optional[int]
    total_patients: int
    critical_patients: int
    new_admissions: int
    discharges: int
    general_notes: Optional[str]
    pending_tasks: List[str]
    critical_alerts: List[str]
    patient_summaries: List[dict]
    created_at: datetime
    class Config:
        from_attributes = True
