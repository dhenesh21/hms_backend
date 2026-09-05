from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.opd import VisitStatus


class PrescriptionCreate(BaseModel):
    drug_name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = None
    route: Optional[str] = "oral"
    instructions: Optional[str] = None
    quantity: Optional[int] = None


class PrescriptionResponse(BaseModel):
    id: int
    drug_name: str
    generic_name: Optional[str]
    dosage: Optional[str]
    frequency: Optional[str]
    duration_days: Optional[int]
    route: Optional[str]
    instructions: Optional[str]
    quantity: Optional[int]
    is_dispensed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OPDVisitCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    # Vitals
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    # Consultation
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    physical_examination: Optional[str] = None
    clinical_notes: Optional[str] = None
    # Diagnosis
    primary_diagnosis: Optional[str] = None
    secondary_diagnosis: Optional[str] = None
    icd_codes: Optional[List[str]] = []
    # Plan
    treatment_plan: Optional[str] = None
    advice: Optional[str] = None
    diet_advice: Optional[str] = None
    activity_advice: Optional[str] = None
    # Follow-up
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = None
    # Referral
    referred_to: Optional[str] = None
    referral_notes: Optional[str] = None
    # Prescriptions
    prescriptions: List[PrescriptionCreate] = []


class OPDVisitUpdate(BaseModel):
    status: Optional[VisitStatus] = None
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    physical_examination: Optional[str] = None
    clinical_notes: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    secondary_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    advice: Optional[str] = None
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = None
    referred_to: Optional[str] = None
    referral_notes: Optional[str] = None


class OPDVisitResponse(BaseModel):
    id: int
    visit_number: str
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int]
    visit_date: datetime
    status: VisitStatus
    temperature: Optional[float]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    pulse_rate: Optional[int]
    oxygen_saturation: Optional[float]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    bmi: Optional[float]
    chief_complaint: Optional[str]
    primary_diagnosis: Optional[str]
    secondary_diagnosis: Optional[str]
    treatment_plan: Optional[str]
    advice: Optional[str]
    follow_up_required: bool
    follow_up_date: Optional[date]
    referred_to: Optional[str]
    prescriptions: List[PrescriptionResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
