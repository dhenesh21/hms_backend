from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.cpoe import OrderType, OrderPriority, OrderStatus


class OrderSetCreate(BaseModel):
    name: str
    department: Optional[str] = None
    description: Optional[str] = None
    specialty: Optional[str] = None
    items: List[dict] = []


class OrderSetResponse(BaseModel):
    id: int
    name: str
    department: Optional[str]
    specialty: Optional[str]
    items: List[dict]
    is_active: bool

    class Config:
        from_attributes = True


class ClinicalOrderCreate(BaseModel):
    patient_id: int
    ordering_doctor_id: int
    order_type: OrderType
    item_name: str
    instructions: Optional[str] = None
    priority: OrderPriority = OrderPriority.ROUTINE
    source: Optional[str] = None
    source_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    order_set_id: Optional[int] = None
    scheduled_time: Optional[datetime] = None


class OrderSetApply(BaseModel):
    patient_id: int
    ordering_doctor_id: int
    source: Optional[str] = None
    source_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None


class ClinicalOrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    cancelled_reason: Optional[str] = None
    fulfilled_module: Optional[str] = None
    fulfilled_ref_id: Optional[int] = None


class ClinicalOrderResponse(BaseModel):
    id: int
    patient_id: int
    ordering_doctor_id: int
    order_type: OrderType
    item_name: str
    instructions: Optional[str]
    priority: OrderPriority
    status: OrderStatus
    source: Optional[str]
    source_id: Optional[int]
    safety_check_result: Optional[Any]
    scheduled_time: Optional[datetime]
    acknowledged_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class OrderNoteCreate(BaseModel):
    order_id: int
    note: str


class OrderNoteResponse(BaseModel):
    id: int
    order_id: int
    note: str
    author_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
