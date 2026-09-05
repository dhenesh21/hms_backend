from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class UnifiedStaffEntry(BaseModel):
    """
    Item 171 — one row per person, whether they're a doctor, general staff,
    or both. Built by joining DoctorProfile.staff_profile_id (added this
    session) against StaffProfile, NOT a new physical table - see
    doctor.py's DoctorProfile docstring for why a real table merge was
    avoided.
    """
    user_id: int
    full_name: str
    email: str
    phone: Optional[str]

    is_doctor: bool
    doctor_profile_id: Optional[int] = None
    specialization: Optional[str] = None
    registration_number: Optional[str] = None

    is_staff: bool
    staff_profile_id: Optional[int] = None
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    date_of_joining: Optional[date] = None
    is_active: bool = True


class LinkDoctorToStaffRequest(BaseModel):
    doctor_profile_id: int
    staff_profile_id: int
