from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.anesthesia import ASAGrade, FastingStatus


class PreAnesthesiaCreate(BaseModel):
    patient_id: int
    surgery_id: int
    anesthesiologist_id: int
    asa_grade: Optional[ASAGrade] = None
    airway_assessment: Optional[str] = None
    fasting_status: FastingStatus = FastingStatus.NOT_CONFIRMED
    comorbidities_reviewed: bool = False
    allergies_reviewed: bool = False
    previous_anesthesia_issues: Optional[str] = None
    planned_technique: Optional[str] = None
    investigations_reviewed: Optional[str] = None
    fitness_for_anesthesia: Optional[bool] = None
    remarks: Optional[str] = None


class PreAnesthesiaResponse(BaseModel):
    id: int
    surgery_id: int
    anesthesiologist_id: int
    asa_grade: Optional[ASAGrade]
    fasting_status: FastingStatus
    fitness_for_anesthesia: Optional[bool]
    assessed_at: datetime

    class Config:
        from_attributes = True


class AnesthesiaRecordCreate(BaseModel):
    surgery_id: int
    anesthesiologist_id: int
    technique_used: Optional[str] = None
    induction_time: Optional[datetime] = None


class AnesthesiaRecordUpdate(BaseModel):
    intubation_time: Optional[datetime] = None
    extubation_time: Optional[datetime] = None
    drugs_administered: Optional[List[dict]] = None
    fluids_administered: Optional[List[dict]] = None
    blood_products_used: Optional[List[dict]] = None
    intraop_events: Optional[str] = None
    total_blood_loss_ml: Optional[int] = None
    total_urine_output_ml: Optional[int] = None


class AnesthesiaRecordResponse(BaseModel):
    id: int
    surgery_id: int
    anesthesiologist_id: int
    technique_used: Optional[str]
    induction_time: Optional[datetime]
    intubation_time: Optional[datetime]
    extubation_time: Optional[datetime]
    drugs_administered: Any
    intraop_events: Optional[str]

    class Config:
        from_attributes = True


class AnesthesiaVitalCreate(BaseModel):
    anesthesia_record_id: int
    heart_rate: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    spo2: Optional[float] = None
    etco2: Optional[float] = None
    temperature: Optional[float] = None


class AnesthesiaVitalResponse(BaseModel):
    id: int
    anesthesia_record_id: int
    recorded_at: datetime
    heart_rate: Optional[int]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    spo2: Optional[float]

    class Config:
        from_attributes = True
