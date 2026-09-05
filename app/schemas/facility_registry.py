from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.facility_registry import FacilityType


class FacilityRegistryCreate(BaseModel):
    facility_type: FacilityType
    name: str
    national_facility_id: Optional[str] = None
    is_self: bool = False
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class FacilityRegistryUpdate(BaseModel):
    is_verified: Optional[bool] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class FacilityRegistryResponse(BaseModel):
    id: int
    facility_type: FacilityType
    name: str
    national_facility_id: Optional[str]
    is_self: bool
    city: Optional[str]
    is_verified: bool

    class Config:
        from_attributes = True
