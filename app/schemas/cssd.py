from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.cssd import SterilizationMethod, CycleStatus


class CycleCreate(BaseModel):
    item_set_name: str
    quantity: int = 1
    source_department: Optional[str] = None
    method: SterilizationMethod = SterilizationMethod.AUTOCLAVE
    batch_indicator_number: Optional[str] = None
    notes: Optional[str] = None


class QualityCheckRequest(BaseModel):
    passed: bool
    notes: Optional[str] = None


class DispatchRequest(BaseModel):
    dispatched_to: str


class CycleResponse(BaseModel):
    id: int
    cycle_number: str
    item_set_name: str
    quantity: int
    source_department: Optional[str]
    method: SterilizationMethod
    status: CycleStatus
    received_at: datetime
    sterilization_start: Optional[datetime]
    sterilization_end: Optional[datetime]
    quality_check_passed: Optional[str]
    dispatched_at: Optional[datetime]
    dispatched_to: Optional[str]
    batch_indicator_number: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True
