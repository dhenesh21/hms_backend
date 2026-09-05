from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.patient_category import PatientCategory


class PatientCategoryProfileUpsert(BaseModel):
    patient_id: int
    category: PatientCategory
    country_of_origin: Optional[str] = None
    passport_number: Optional[str] = None
    visa_number: Optional[str] = None
    visa_expiry: Optional[date] = None
    preferred_language: Optional[str] = None
    interpreter_required: bool = False
    facilitator_agency: Optional[str] = None
    corporate_employer_name: Optional[str] = None
    corporate_employee_id: Optional[str] = None
    corporate_scheme_name: Optional[str] = None
    corporate_tpa_id: Optional[int] = None
    notes: Optional[str] = None


class PatientCategoryProfileResponse(BaseModel):
    id: int
    patient_id: int
    category: PatientCategory
    country_of_origin: Optional[str]
    passport_number: Optional[str]
    preferred_language: Optional[str]
    interpreter_required: bool
    corporate_employer_name: Optional[str]
    corporate_scheme_name: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
