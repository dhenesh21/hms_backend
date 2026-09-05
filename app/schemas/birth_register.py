from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.birth_register import BabyGender, DeliveryType, BirthStatus


class BabyCreate(BaseModel):
    baby_name: Optional[str] = None
    gender: BabyGender
    birth_status: BirthStatus = BirthStatus.LIVE_BIRTH
    birth_weight_grams: Optional[float] = None
    birth_length_cm: Optional[float] = None
    apgar_score_1min: Optional[int] = None
    apgar_score_5min: Optional[int] = None
    birth_defects_notes: Optional[str] = None
    resuscitation_required: bool = False


class BabyResponse(BabyCreate):
    id: int
    birth_register_id: int
    baby_patient_id: Optional[int]
    certificate_number: Optional[str]
    certificate_issued: bool
    certificate_issued_date: Optional[datetime]

    class Config:
        from_attributes = True


class BirthRegisterCreate(BaseModel):
    mother_patient_id: int
    mother_ipd_admission_id: Optional[int] = None
    delivery_type: DeliveryType = DeliveryType.NORMAL_VAGINAL
    attending_doctor_id: Optional[int] = None
    gravida: Optional[int] = None
    para: Optional[int] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    babies: list[BabyCreate]  # at least one - twins/triplets add more


class BirthRegisterResponse(BaseModel):
    id: int
    birth_register_number: str
    mother_patient_id: int
    mother_ipd_admission_id: Optional[int]
    delivery_datetime: datetime
    delivery_type: DeliveryType
    attending_doctor_id: Optional[int]
    gravida: Optional[int]
    para: Optional[int]
    complications: Optional[str]
    notes: Optional[str]
    babies: list[BabyResponse] = []

    class Config:
        from_attributes = True


class CertificateIssueRequest(BaseModel):
    certificate_number: str


class LinkBabyToPatientRequest(BaseModel):
    baby_patient_id: int
