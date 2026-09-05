from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LogAccessRequest(BaseModel):
    patient_id: int
    resource_type: str
    resource_id: Optional[str] = None
    access_reason: Optional[str] = None


class AccessLogResponse(BaseModel):
    id: int
    patient_id: int
    accessed_by: int
    resource_type: str
    resource_id: Optional[str]
    access_reason: Optional[str]
    was_restricted_record: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PrivacyFlagCreate(BaseModel):
    patient_id: int
    reason: str


class PrivacyFlagResponse(BaseModel):
    id: int
    patient_id: int
    reason: str
    flagged_by: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
