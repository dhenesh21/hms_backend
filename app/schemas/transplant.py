from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from app.models.transplant import OrganType, DonorType, WaitlistStatus


class CandidateCreate(BaseModel):
    patient_id: int
    transplant_surgeon_id: int
    organ_needed: OrganType
    blood_group: Optional[str] = None
    urgency_score: Optional[int] = None


class CandidateUpdate(BaseModel):
    status: Optional[WaitlistStatus] = None
    urgency_score: Optional[int] = None
    workup_complete: Optional[bool] = None
    hla_typing_done: Optional[bool] = None
    ethics_committee_cleared: Optional[bool] = None
    removed_reason: Optional[str] = None


class CandidateResponse(BaseModel):
    id: int
    patient_id: int
    organ_needed: OrganType
    blood_group: Optional[str]
    listed_date: date
    urgency_score: Optional[int]
    status: WaitlistStatus
    workup_complete: bool
    hla_typing_done: bool

    class Config:
        from_attributes = True


class TransplantCaseCreate(BaseModel):
    candidate_id: int
    patient_id: int
    transplant_surgeon_id: int
    organ: OrganType
    donor_type: DonorType
    donor_patient_id: Optional[int] = None
    donor_relation: Optional[str] = None
    surgery_date: Optional[date] = None
    cross_match_result: Optional[str] = None
    immunosuppression_protocol: Optional[str] = None


class TransplantCaseUpdate(BaseModel):
    surgery_date: Optional[date] = None
    ot_surgery_id: Optional[int] = None
    cross_match_result: Optional[str] = None
    immunosuppression_protocol: Optional[str] = None
    outcome: Optional[str] = None


class TransplantCaseResponse(BaseModel):
    id: int
    candidate_id: int
    patient_id: int
    organ: OrganType
    donor_type: DonorType
    surgery_date: Optional[date]
    outcome: Optional[str]

    class Config:
        from_attributes = True


class FollowUpCreate(BaseModel):
    case_id: int
    days_post_transplant: Optional[int] = None
    graft_function_status: Optional[str] = None
    rejection_signs: bool = False
    immunosuppression_levels: Optional[dict] = None
    medication_adjustment: Optional[str] = None
    notes: Optional[str] = None


class FollowUpResponse(BaseModel):
    id: int
    case_id: int
    visit_date: date
    graft_function_status: Optional[str]
    rejection_signs: bool

    class Config:
        from_attributes = True
