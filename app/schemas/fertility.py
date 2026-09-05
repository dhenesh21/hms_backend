from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from app.models.fertility import TreatmentType, FertilityCycleStatus


class FertilityProfileCreate(BaseModel):
    patient_id: int
    fertility_specialist_id: int
    partner_patient_id: Optional[int] = None
    partner_name: Optional[str] = None
    diagnosis: Optional[str] = None
    amh_level: Optional[float] = None


class FertilityProfileResponse(BaseModel):
    id: int
    patient_id: int
    partner_name: Optional[str]
    diagnosis: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class FertilityCycleCreate(BaseModel):
    profile_id: int
    treatment_type: TreatmentType
    cycle_start_date: Optional[date] = None
    stimulation_protocol: Optional[str] = None


class FertilityCycleUpdate(BaseModel):
    status: Optional[FertilityCycleStatus] = None
    eggs_retrieved: Optional[int] = None
    embryos_created: Optional[int] = None
    embryos_transferred: Optional[int] = None
    embryos_frozen: Optional[int] = None
    transfer_date: Optional[date] = None
    pregnancy_test_date: Optional[date] = None
    pregnancy_test_result: Optional[str] = None
    notes: Optional[str] = None


class FertilityCycleResponse(BaseModel):
    id: int
    profile_id: int
    treatment_type: TreatmentType
    status: FertilityCycleStatus
    cycle_start_date: Optional[date]
    eggs_retrieved: Optional[int]
    embryos_transferred: Optional[int]
    pregnancy_test_result: Optional[str]

    class Config:
        from_attributes = True


class MonitoringVisitCreate(BaseModel):
    cycle_id: int
    day_of_cycle: Optional[int] = None
    follicle_counts: Optional[dict] = None
    endometrial_thickness_mm: Optional[float] = None
    estradiol_level: Optional[float] = None
    lh_level: Optional[float] = None
    medication_adjustment: Optional[str] = None


class MonitoringVisitResponse(BaseModel):
    id: int
    cycle_id: int
    visit_date: date
    day_of_cycle: Optional[int]
    follicle_counts: Any
    endometrial_thickness_mm: Optional[float]

    class Config:
        from_attributes = True
