from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.emr import AllergyType, AllergySeverity, DocumentType


class AllergyCreate(BaseModel):
    patient_id: int
    allergen: str
    allergy_type: AllergyType = AllergyType.DRUG
    severity: AllergySeverity = AllergySeverity.MILD
    reaction: Optional[str] = None
    reported_date: Optional[date] = None


class AllergyResponse(BaseModel):
    id: int
    patient_id: int
    allergen: str
    allergy_type: AllergyType
    severity: AllergySeverity
    reaction: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChronicConditionCreate(BaseModel):
    patient_id: int
    condition_name: str
    icd_code: Optional[str] = None
    diagnosed_date: Optional[date] = None
    diagnosed_by: Optional[str] = None
    current_status: Optional[str] = "active"
    notes: Optional[str] = None


class ChronicConditionResponse(BaseModel):
    id: int
    patient_id: int
    condition_name: str
    icd_code: Optional[str]
    diagnosed_date: Optional[date]
    current_status: Optional[str]
    notes: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class MedicationHistoryCreate(BaseModel):
    patient_id: int
    drug_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribed_by: Optional[str] = None
    reason: Optional[str] = None
    is_current: bool = True


class MedicationHistoryResponse(BaseModel):
    id: int
    patient_id: int
    drug_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool

    class Config:
        from_attributes = True


class FamilyHistoryCreate(BaseModel):
    patient_id: int
    relation: str
    condition: str
    age_of_onset: Optional[int] = None
    notes: Optional[str] = None


class FamilyHistoryResponse(BaseModel):
    id: int
    patient_id: int
    relation: str
    condition: str
    age_of_onset: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True


class SurgicalHistoryCreate(BaseModel):
    patient_id: int
    procedure_name: str
    surgery_date: Optional[date] = None
    surgeon: Optional[str] = None
    hospital: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None


class SurgicalHistoryResponse(BaseModel):
    id: int
    patient_id: int
    procedure_name: str
    surgery_date: Optional[date]
    surgeon: Optional[str]
    hospital: Optional[str]
    complications: Optional[str]

    class Config:
        from_attributes = True


class ImmunizationCreate(BaseModel):
    patient_id: int
    vaccine_name: str
    dose_number: int = 1
    administered_date: date
    administered_by: Optional[str] = None
    batch_number: Optional[str] = None
    next_due_date: Optional[date] = None
    notes: Optional[str] = None


class ImmunizationResponse(BaseModel):
    id: int
    patient_id: int
    vaccine_name: str
    dose_number: int
    administered_date: date
    next_due_date: Optional[date]

    class Config:
        from_attributes = True


class ClinicalDocumentCreate(BaseModel):
    patient_id: int
    document_type: DocumentType
    title: str
    description: Optional[str] = None
    file_name: Optional[str] = None
    source: Optional[str] = None
    document_date: Optional[date] = None
    ipd_admission_id: Optional[int] = None
    opd_visit_id: Optional[int] = None
    tags: List[str] = []


class ClinicalDocumentResponse(BaseModel):
    id: int
    patient_id: int
    document_type: DocumentType
    title: str
    description: Optional[str]
    file_name: Optional[str]
    source: Optional[str]
    document_date: Optional[date]
    tags: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosisRecordCreate(BaseModel):
    patient_id: int
    diagnosis: str
    icd_code: Optional[str] = None
    diagnosis_type: str = "primary"
    diagnosis_date: Optional[date] = None
    source: str = "opd"
    source_id: Optional[int] = None
    notes: Optional[str] = None


class DiagnosisRecordResponse(BaseModel):
    id: int
    patient_id: int
    diagnosis: str
    icd_code: Optional[str]
    diagnosis_type: str
    diagnosis_date: Optional[date]
    source: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class PatientEMRResponse(BaseModel):
    patient_id: int
    allergies: List[AllergyResponse]
    chronic_conditions: List[ChronicConditionResponse]
    medication_history: List[MedicationHistoryResponse]
    family_history: List[FamilyHistoryResponse]
    surgical_history: List[SurgicalHistoryResponse]
    immunizations: List[ImmunizationResponse]
    documents: List[ClinicalDocumentResponse]
    diagnosis_records: List[DiagnosisRecordResponse]
