from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


class TimelineEvent(BaseModel):
    event_time: datetime
    event_type: str      # diagnosis, order, form, consent, vital, admission
    category: Optional[str] = None
    title: str
    detail: Optional[str] = None
    is_critical: bool = False
    ref_id: Optional[int] = None


class CriticalResultAlert(BaseModel):
    patient_id: int
    lab_order_item_id: int
    test_name: str
    result_value: Optional[str]
    result_status: Optional[str]
    reported_at: Optional[datetime]


class PatientSummary(BaseModel):
    """
    Items 233/234 (Clinical Data Repository / Longitudinal Patient Record) —
    a single consolidated "current state" snapshot, distinct from the flat
    chronological timeline above: this is what a clinician wants at a
    glance (active problems, allergies, current meds, active care plans),
    not a scrollable history. Built entirely from tables that already exist
    across EMR/CPOE/Care Plans — no new storage, pure read aggregation.
    """
    patient_id: int
    active_allergies: List[dict]
    active_chronic_conditions: List[dict]
    current_medications: List[dict]
    active_care_plans: List[dict]
    open_clinical_orders: List[dict]
    generated_at: datetime
