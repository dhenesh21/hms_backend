from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.data_exchange import DataCategory, ExchangeAuthStatus


class ExchangeAuthCreate(BaseModel):
    patient_id: int
    authorized_facility_id: Optional[int] = None
    authorized_provider_id: Optional[int] = None
    authorized_party_name_freetext: Optional[str] = None
    data_categories: List[DataCategory] = []
    purpose: Optional[str] = None
    consented_by_name: Optional[str] = None
    signature_data: Optional[str] = None
    expires_at: Optional[datetime] = None


class ExchangeAuthRevoke(BaseModel):
    revoked_reason: str


class ExchangeAuthResponse(BaseModel):
    id: int
    patient_id: int
    authorized_facility_id: Optional[int]
    authorized_provider_id: Optional[int]
    authorized_party_name_freetext: Optional[str]
    data_categories: Any
    status: ExchangeAuthStatus
    granted_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExchangeLogCreate(BaseModel):
    authorization_id: int
    data_category: DataCategory
    record_count: Optional[int] = None


class ExchangeLogResponse(BaseModel):
    id: int
    authorization_id: int
    data_category: DataCategory
    record_count: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ExchangeCheckResult(BaseModel):
    authorized: bool
    reason: Optional[str] = None
    matching_authorization_id: Optional[int] = None
