from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.front_desk import VisitorStatus, LostFoundStatus, LostFoundType


class VisitorCheckIn(BaseModel):
    visitor_name: str
    visitor_phone: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None
    relation_to_patient: Optional[str] = None
    patient_id: int
    ipd_admission_id: Optional[int] = None
    notes: Optional[str] = None


class VisitorResponse(BaseModel):
    id: int
    pass_number: str
    visitor_name: str
    visitor_phone: Optional[str]
    id_proof_type: Optional[str]
    id_proof_number: Optional[str]
    relation_to_patient: Optional[str]
    patient_id: int
    ipd_admission_id: Optional[int]
    status: VisitorStatus
    check_in_time: datetime
    check_out_time: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True


class LostFoundCreate(BaseModel):
    entry_type: LostFoundType = LostFoundType.FOUND_ITEM
    item_description: str
    location_found_lost: Optional[str] = None
    patient_id: Optional[int] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    notes: Optional[str] = None


class LostFoundClaim(BaseModel):
    claimed_by: str
    claim_verification: Optional[str] = None


class LostFoundResponse(BaseModel):
    id: int
    item_number: str
    entry_type: LostFoundType
    item_description: str
    location_found_lost: Optional[str]
    patient_id: Optional[int]
    reporter_name: Optional[str]
    reporter_phone: Optional[str]
    status: LostFoundStatus
    date_reported: datetime
    claimed_by: Optional[str]
    claimed_date: Optional[datetime]
    claim_verification: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True
