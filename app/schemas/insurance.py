from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.insurance import ClaimStatus


class InsuranceCompanyCreate(BaseModel):
    company_code: str
    name: str
    tpa_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    claim_submission_email: Optional[str] = None
    portal_url: Optional[str] = None


class InsuranceCompanyResponse(BaseModel):
    id: int
    company_code: str
    name: str
    tpa_name: Optional[str]
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class PolicyCreate(BaseModel):
    policy_number: str
    patient_id: int
    company_id: int
    tpa_id: Optional[str] = None
    policy_holder_name: str
    relation_to_patient: str = "self"
    sum_insured: float
    policy_start_date: date
    policy_end_date: date
    room_rent_limit: Optional[float] = None
    icu_limit: Optional[float] = None
    copay_percent: float = 0.0
    deductible_amount: float = 0.0
    pre_existing_covered: bool = False
    waiting_period_days: int = 30
    network_hospital: bool = True
    card_number: Optional[str] = None
    group_policy: bool = False
    employer_name: Optional[str] = None


class PolicyResponse(BaseModel):
    id: int
    policy_number: str
    patient_id: int
    company_id: int
    policy_holder_name: str
    relation_to_patient: str
    sum_insured: float
    policy_start_date: date
    policy_end_date: date
    room_rent_limit: Optional[float]
    icu_limit: Optional[float]
    copay_percent: float
    deductible_amount: float
    pre_existing_covered: bool
    network_hospital: bool
    card_number: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class PreAuthRequest(BaseModel):
    claim_id: int
    preauth_number: Optional[str] = None
    preauth_approved_amount: Optional[float] = None
    preauth_validity_date: Optional[date] = None
    preauth_notes: Optional[str] = None
    approved: bool = True


class ClaimCreate(BaseModel):
    policy_id: int
    patient_id: int
    ipd_admission_id: Optional[int] = None
    bill_id: Optional[int] = None
    admission_diagnosis: Optional[str] = None
    icd_codes: List[str] = []
    procedure_codes: List[str] = []
    treating_doctor: Optional[str] = None
    claimed_amount: float = 0.0
    remarks: Optional[str] = None


class ClaimUpdate(BaseModel):
    status: Optional[ClaimStatus] = None
    approved_amount: Optional[float] = None
    rejected_amount: Optional[float] = None
    deductible_applied: Optional[float] = None
    copay_amount: Optional[float] = None
    non_payable_amount: Optional[float] = None
    submission_reference: Optional[str] = None
    settlement_reference: Optional[str] = None
    rejection_reason: Optional[str] = None
    non_payable_reason: Optional[str] = None
    appeal_reason: Optional[str] = None
    remarks: Optional[str] = None


class ClaimDocumentCreate(BaseModel):
    claim_id: int
    document_type: str
    document_name: str
    file_path: Optional[str] = None


class ClaimDocumentResponse(BaseModel):
    id: int
    claim_id: int
    document_type: str
    document_name: str
    uploaded_at: datetime
    class Config:
        from_attributes = True


class ClaimResponse(BaseModel):
    id: int
    claim_number: str
    policy_id: int
    patient_id: int
    ipd_admission_id: Optional[int]
    bill_id: Optional[int]
    status: ClaimStatus
    preauth_number: Optional[str]
    preauth_approved_amount: Optional[float]
    preauth_validity_date: Optional[date]
    admission_diagnosis: Optional[str]
    claimed_amount: float
    approved_amount: float
    rejected_amount: float
    deductible_applied: float
    copay_amount: float
    non_payable_amount: float
    submitted_at: Optional[datetime]
    settled_at: Optional[datetime]
    settlement_reference: Optional[str]
    rejection_reason: Optional[str]
    documents: List[ClaimDocumentResponse] = []
    remarks: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True
