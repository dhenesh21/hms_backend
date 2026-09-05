from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.family import RelationType


class FamilyMemberCreate(BaseModel):
    patient_id: int
    linked_patient_id: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    relation_type: RelationType
    is_emergency_contact: bool = False
    is_authorized_proxy: bool = False
    proxy_scope_notes: Optional[str] = None


class FamilyMemberResponse(BaseModel):
    id: int
    patient_id: int
    linked_patient_id: Optional[int]
    name: Optional[str]
    phone: Optional[str]
    relation_type: RelationType
    is_emergency_contact: bool
    is_authorized_proxy: bool

    class Config:
        from_attributes = True


class FamilyHealthSummary(BaseModel):
    """One linked family member's high-level status — item 196. Deliberately
    coarse (no diagnoses/records) since this is visible to another family
    member, not the patient themself; full records still require that
    person's own portal login and consent."""
    linked_patient_id: int
    relation_type: RelationType
    has_upcoming_appointment: bool
    has_active_ipd_admission: bool
