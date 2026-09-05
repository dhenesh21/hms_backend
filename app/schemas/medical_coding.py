from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.medical_coding import MedicalCodingCodeSystem, CodeType


class MedicalCodeCreate(BaseModel):
    code_system: MedicalCodingCodeSystem
    code: str
    description: str


class MedicalCodeResponse(BaseModel):
    id: int
    code_system: MedicalCodingCodeSystem
    code: str
    description: str

    class Config:
        from_attributes = True


class PatientCodingCreate(BaseModel):
    bill_id: int
    patient_id: int
    code_id: int
    code_type: CodeType
    notes: Optional[str] = None


class PatientCodingResponse(BaseModel):
    id: int
    bill_id: int
    patient_id: int
    code_id: int
    code_type: CodeType
    notes: Optional[str]
    coded_at: datetime

    class Config:
        from_attributes = True


class RCMWorklistItem(BaseModel):
    bill_id: int
    bill_number: str
    patient_id: int
    gross_total: float
    has_diagnosis_code: bool
    has_procedure_code: bool
    is_coding_complete: bool
    insurance_claim_id: Optional[int]
    ready_for_claim_submission: bool
