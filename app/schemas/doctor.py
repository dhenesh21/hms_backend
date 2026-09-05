from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.appointment import AppointmentStatus, AppointmentType


class DoctorProfileCreate(BaseModel):
    user_id: int
    registration_number: str
    specialization: str
    sub_specialization: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: int = 0
    consultation_fee: float = 0.0
    bio: Optional[str] = None
    languages_spoken: List[str] = []
    available_days: List[str] = []
    consultation_duration_minutes: int = 15


class DoctorProfileResponse(BaseModel):
    id: int
    user_id: int
    registration_number: str
    specialization: str
    sub_specialization: Optional[str]
    qualification: Optional[str]
    experience_years: int
    consultation_fee: float
    bio: Optional[str]
    languages_spoken: List[str]
    available_days: List[str]
    consultation_duration_minutes: int
    is_available: bool

    class Config:
        from_attributes = True


class DoctorWithUserResponse(BaseModel):
    id: int
    doctor_profile_id: Optional[int] = None
    registration_number: str
    specialization: str
    consultation_fee: float
    experience_years: int
    is_available: bool
    full_name: str
    email: str
    department: Optional[str]
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class DutyRosterCreate(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str
    max_patients: int = 20


class DutyRosterResponse(BaseModel):
    id: int
    doctor_id: int
    day_of_week: str
    start_time: str
    end_time: str
    max_patients: int
    is_active: bool

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: str
    appointment_type: AppointmentType = AppointmentType.CONSULTATION
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    cancelled_reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    appointment_number: str
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: str
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason: Optional[str]
    notes: Optional[str]
    token_number: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class AppointmentDetailResponse(AppointmentResponse):
    patient_name: str
    patient_uhid: str
    doctor_name: str
    specialization: str
