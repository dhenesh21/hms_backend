from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.provider_registry import ProviderType


class ProviderRegistryCreate(BaseModel):
    provider_type: ProviderType
    national_registry_id: Optional[str] = None
    full_name: str
    specialization: Optional[str] = None
    registration_council: Optional[str] = None
    registration_valid_until: Optional[date] = None
    linked_doctor_profile_id: Optional[int] = None
    is_internal: bool = False
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class ProviderRegistryUpdate(BaseModel):
    is_verified: Optional[bool] = None
    registration_valid_until: Optional[date] = None
    notes: Optional[str] = None


class ProviderRegistryResponse(BaseModel):
    id: int
    provider_type: ProviderType
    national_registry_id: Optional[str]
    full_name: str
    specialization: Optional[str]
    is_internal: bool
    is_verified: bool

    class Config:
        from_attributes = True
