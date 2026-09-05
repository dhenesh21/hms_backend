from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date
from app.models.patient_portal import FeedbackCategory, GrievanceStatus


class PatientPortalRegister(BaseModel):
    uhid: str                 # links to existing Patient by hospital ID
    phone: str
    email: Optional[str] = None
    password: str


class PatientPortalLogin(BaseModel):
    phone: str
    password: str


class PatientPortalTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient_id: int


class PatientPortalMeResponse(BaseModel):
    id: int
    patient_id: int
    phone: str
    email: Optional[str]

    class Config:
        from_attributes = True


class MyAppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    appointment_date: date
    status: str

    class Config:
        from_attributes = True


class MyOPDVisitResponse(BaseModel):
    id: int
    visit_number: str
    doctor_id: int
    visit_date: Any

    class Config:
        from_attributes = True


class MyIPDAdmissionResponse(BaseModel):
    id: int
    admission_number: str
    admission_date: datetime
    discharge_date: Optional[datetime]
    status: str
    diagnosis_at_admission: Optional[str]

    class Config:
        from_attributes = True


class MyLabOrderResponse(BaseModel):
    id: int
    order_number: str
    ordered_at: datetime

    class Config:
        from_attributes = True


class MyBillResponse(BaseModel):
    id: int
    bill_number: str
    bill_type: str
    status: str
    gross_total: float
    paid_amount: float
    bill_date: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    source: Optional[str] = None
    source_id: Optional[int] = None
    category: FeedbackCategory = FeedbackCategory.OVERALL
    rating: int
    comments: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    category: FeedbackCategory
    rating: int
    comments: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class GrievanceCreate(BaseModel):
    subject: str
    description: str
    department_concerned: Optional[str] = None


class GrievanceResponse(BaseModel):
    id: int
    subject: str
    description: str
    status: GrievanceStatus
    resolution_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class GrievanceStaffUpdate(BaseModel):
    status: GrievanceStatus
    resolution_notes: Optional[str] = None
    assigned_to: Optional[int] = None
