from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from app.models.oncology import CancerStage, TreatmentIntent, ChemoCycleStatus


class OncologyCaseCreate(BaseModel):
    patient_id: int
    oncologist_id: int
    primary_site: str
    histology: Optional[str] = None
    stage: CancerStage = CancerStage.UNKNOWN
    diagnosis_date: Optional[date] = None
    treatment_intent: Optional[TreatmentIntent] = None
    chemo_protocol_name: Optional[str] = None


class OncologyCaseUpdate(BaseModel):
    stage: Optional[CancerStage] = None
    tumor_board_reviewed: Optional[bool] = None
    tumor_board_notes: Optional[str] = None
    chemo_protocol_name: Optional[str] = None
    is_active: Optional[bool] = None


class OncologyCaseResponse(BaseModel):
    id: int
    patient_id: int
    primary_site: str
    stage: CancerStage
    treatment_intent: Optional[TreatmentIntent]
    tumor_board_reviewed: bool
    chemo_protocol_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class ChemoCycleCreate(BaseModel):
    case_id: int
    cycle_number: int
    scheduled_date: date


class ChemoCycleUpdate(BaseModel):
    status: Optional[ChemoCycleStatus] = None
    drugs_administered: Optional[List[dict]] = None
    pre_cycle_labs_reviewed: Optional[bool] = None
    toxicity_grade: Optional[int] = None
    adverse_events: Optional[str] = None
    delay_reason: Optional[str] = None


class ChemoCycleResponse(BaseModel):
    id: int
    case_id: int
    cycle_number: int
    scheduled_date: date
    status: ChemoCycleStatus
    toxicity_grade: Optional[int]

    class Config:
        from_attributes = True


class FollowUpCreate(BaseModel):
    case_id: int
    response_assessment: Optional[str] = None
    imaging_reviewed: bool = False
    notes: Optional[str] = None
    next_follow_up_date: Optional[date] = None


class FollowUpResponse(BaseModel):
    id: int
    case_id: int
    visit_date: date
    response_assessment: Optional[str]
    next_follow_up_date: Optional[date]

    class Config:
        from_attributes = True
