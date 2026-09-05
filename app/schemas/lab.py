from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.lab import LabCategory, SampleStatus, LabPriority


class LabTestCreate(BaseModel):
    test_code: str
    test_name: str
    category: LabCategory
    sample_type: str
    normal_range: Optional[str] = None
    unit: Optional[str] = None
    methodology: Optional[str] = None
    turnaround_time_hours: int = 24
    price: float = 0.0
    instructions: Optional[str] = None


class LabTestResponse(BaseModel):
    id: int
    test_code: str
    test_name: str
    category: LabCategory
    sample_type: str
    normal_range: Optional[str]
    unit: Optional[str]
    price: float
    turnaround_time_hours: int
    is_active: bool

    class Config:
        from_attributes = True


class LabOrderCreate(BaseModel):
    patient_id: int
    ordered_by: int
    priority: LabPriority = LabPriority.ROUTINE
    opd_visit_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    clinical_info: Optional[str] = None
    test_ids: List[int]


class LabSubResultCreate(BaseModel):
    parameter_name: str
    result_value: Optional[str] = None
    result_numeric: Optional[float] = None
    unit: Optional[str] = None
    normal_range: Optional[str] = None
    result_status: Optional[str] = None


class LabResultEntry(BaseModel):
    order_item_id: int
    result_value: Optional[str] = None
    result_numeric: Optional[float] = None
    result_unit: Optional[str] = None
    result_status: Optional[str] = None   # normal, high, low, critical
    normal_range: Optional[str] = None
    remarks: Optional[str] = None
    sub_results: List[LabSubResultCreate] = []


class LabSubResultResponse(BaseModel):
    id: int
    parameter_name: str
    result_value: Optional[str]
    result_numeric: Optional[float]
    unit: Optional[str]
    normal_range: Optional[str]
    result_status: Optional[str]

    class Config:
        from_attributes = True


class LabOrderItemResponse(BaseModel):
    id: int
    order_id: int
    test_id: int
    status: SampleStatus
    barcode: Optional[str]
    sample_collected_at: Optional[datetime]
    result_value: Optional[str]
    result_numeric: Optional[float]
    result_status: Optional[str]
    normal_range: Optional[str]
    remarks: Optional[str]
    result_entered_at: Optional[datetime]
    approved_at: Optional[datetime]
    sub_results: List[LabSubResultResponse] = []
    test: Optional[LabTestResponse]

    class Config:
        from_attributes = True


class LabOrderResponse(BaseModel):
    id: int
    order_number: str
    patient_id: int
    ordered_by: int
    priority: LabPriority
    clinical_info: Optional[str]
    ordered_at: datetime
    items: List[LabOrderItemResponse] = []

    class Config:
        from_attributes = True


class SampleCollectionUpdate(BaseModel):
    order_item_ids: List[int]
    barcode_prefix: Optional[str] = "LAB"
