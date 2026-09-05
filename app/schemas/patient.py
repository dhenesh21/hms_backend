from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from app.models.patient import Gender, BloodGroup, MaritalStatus


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    blood_group: Optional[BloodGroup] = None
    marital_status: Optional[MaritalStatus] = None
    phone: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_validity: Optional[date] = None
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    blood_group: Optional[BloodGroup] = None
    marital_status: Optional[MaritalStatus] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_validity: Optional[date] = None


class PatientResponse(BaseModel):
    id: int
    uhid: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    blood_group: Optional[BloodGroup]
    marital_status: Optional[MaritalStatus]
    phone: str
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_relation: Optional[str]
    allergies: Optional[str]
    chronic_conditions: Optional[str]
    insurance_provider: Optional[str]
    insurance_policy_number: Optional[str]
    photo_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    id: int
    uhid: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    phone: str
    blood_group: Optional[BloodGroup]
    is_active: bool

    class Config:
        from_attributes = True


class PaginatedPatients(BaseModel):
    total: int
    page: int
    size: int
    patients: List[PatientListResponse]
