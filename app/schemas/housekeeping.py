from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.housekeeping import CleaningTaskType, CleaningTaskStatus, WasteType


class CleaningTaskCreate(BaseModel):
    task_type: CleaningTaskType = CleaningTaskType.ROUTINE
    ward_id: Optional[int] = None
    bed_id: Optional[int] = None
    area_name: Optional[str] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None


class CleaningTaskResponse(BaseModel):
    id: int
    task_type: CleaningTaskType
    status: CleaningTaskStatus
    ward_id: Optional[int]
    bed_id: Optional[int]
    area_name: Optional[str]
    assigned_to: Optional[int]
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    verified_at: Optional[datetime]
    verified_by: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True


class LinenLogCreate(BaseModel):
    ward_id: Optional[int] = None
    item_name: str
    quantity_sent: int
    is_soiled: str = "normal"
    notes: Optional[str] = None


class LinenLogReceive(BaseModel):
    quantity_received: int


class LinenLogResponse(BaseModel):
    id: int
    ward_id: Optional[int]
    item_name: str
    quantity_sent: int
    quantity_received: Optional[int]
    sent_at: datetime
    received_at: Optional[datetime]
    is_soiled: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class WasteLogCreate(BaseModel):
    ward_id: Optional[int] = None
    waste_type: WasteType = WasteType.GENERAL
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class WasteLogDispose(BaseModel):
    disposal_method: str


class WasteLogResponse(BaseModel):
    id: int
    ward_id: Optional[int]
    waste_type: WasteType
    weight_kg: Optional[float]
    collected_at: datetime
    disposed_at: Optional[datetime]
    disposal_method: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True
