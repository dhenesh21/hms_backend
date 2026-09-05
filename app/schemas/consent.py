from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.models.consent import ConsentStatus


class ConsentTemplateCreate(BaseModel):
    name: str
    category: Optional[str] = None
    body_text: str
    requires_witness: bool = False
    validity_days: Optional[int] = None


class ConsentTemplateResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    body_text: str
    requires_witness: bool
    validity_days: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


class PatientConsentCreate(BaseModel):
    patient_id: int
    template_id: int
    source: Optional[str] = None
    source_id: Optional[int] = None
    consented_by_name: Optional[str] = None
    relationship_to_patient: str = "self"
    explained_by: Optional[int] = None
    metadata_json: Optional[Any] = None


class PatientConsentSign(BaseModel):
    consented_by_name: str
    relationship_to_patient: str = "self"
    signature_data: str
    witness_name: Optional[str] = None


class PatientConsentWithdraw(BaseModel):
    withdrawal_reason: str


class PatientConsentResponse(BaseModel):
    id: int
    patient_id: int
    template_id: int
    status: ConsentStatus
    consented_by_name: Optional[str]
    relationship_to_patient: Optional[str]
    witness_name: Optional[str]
    signed_at: Optional[datetime]
    expires_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
