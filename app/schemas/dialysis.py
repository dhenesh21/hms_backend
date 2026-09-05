from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.dialysis import DialysisAccessType, DialysisModality, DialysisSessionStatus


class DialysisProfileCreate(BaseModel):
    patient_id: int
    nephrologist_id: int
    modality: DialysisModality = DialysisModality.HEMODIALYSIS
    access_type: DialysisAccessType
    access_site: Optional[str] = None
    dry_weight_kg: Optional[float] = None
    frequency_per_week: int = 3
    primary_renal_diagnosis: Optional[str] = None


class DialysisProfileResponse(BaseModel):
    id: int
    patient_id: int
    modality: DialysisModality
    access_type: DialysisAccessType
    dry_weight_kg: Optional[float]
    frequency_per_week: int
    is_active: bool

    class Config:
        from_attributes = True


class DialysisSessionCreate(BaseModel):
    profile_id: int
    scheduled_at: datetime
    machine_id: Optional[str] = None


class DialysisSessionUpdate(BaseModel):
    status: Optional[DialysisSessionStatus] = None
    pre_weight_kg: Optional[float] = None
    post_weight_kg: Optional[float] = None
    fluid_removed_ml: Optional[int] = None
    pre_bp_systolic: Optional[int] = None
    pre_bp_diastolic: Optional[int] = None
    post_bp_systolic: Optional[int] = None
    post_bp_diastolic: Optional[int] = None
    complications: Optional[str] = None
    notes: Optional[str] = None


class DialysisSessionResponse(BaseModel):
    id: int
    profile_id: int
    scheduled_at: datetime
    status: DialysisSessionStatus
    pre_weight_kg: Optional[float]
    post_weight_kg: Optional[float]
    fluid_removed_ml: Optional[int]
    complications: Optional[str]

    class Config:
        from_attributes = True
