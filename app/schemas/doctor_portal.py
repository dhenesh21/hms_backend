from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date


class TodayAppointmentResponse(BaseModel):
    id: int
    patient_id: int
    appointment_date: date
    status: str

    class Config:
        from_attributes = True


class MyPatientResponse(BaseModel):
    patient_id: int
    last_visit_date: Any
    last_visit_type: str


class PendingOrderResponse(BaseModel):
    id: int
    patient_id: int
    order_type: str
    item_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MyCarePlanResponse(BaseModel):
    id: int
    patient_id: int
    title: str
    status: str
    started_at: datetime

    class Config:
        from_attributes = True
