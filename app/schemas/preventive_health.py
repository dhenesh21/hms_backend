from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.preventive_health import CheckupBookingStatus


class CheckupBookingCreate(BaseModel):
    patient_id: int
    package_id: int
    scheduled_date: date


class CheckupBookingUpdateStatus(BaseModel):
    status: CheckupBookingStatus
    opd_visit_id: Optional[int] = None
    lab_order_id: Optional[int] = None
    bill_id: Optional[int] = None


class CheckupBookingReview(BaseModel):
    findings_summary: str
    recommendations: Optional[str] = None
    reviewed_by: int


class CheckupBookingResponse(BaseModel):
    id: int
    patient_id: int
    package_id: int
    scheduled_date: date
    status: CheckupBookingStatus
    findings_summary: Optional[str]
    recommendations: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
