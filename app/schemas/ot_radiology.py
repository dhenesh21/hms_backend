from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.ot import OTStatus, SurgeryStatus, AnesthesiaType
from app.models.radiology import ScanType, ScanStatus


# ── OT ────────────────────────────────────────────────
class OTCreate(BaseModel):
    ot_number: str
    name: str
    ot_type: Optional[str] = None
    floor: Optional[int] = None


class OTResponse(BaseModel):
    id: int
    ot_number: str
    name: str
    ot_type: Optional[str]
    floor: Optional[int]
    status: OTStatus
    is_active: bool

    class Config:
        from_attributes = True


class SurgeryCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    ot_id: int
    surgery_date: date
    scheduled_start_time: str
    scheduled_end_time: Optional[str] = None
    primary_surgeon_id: int
    assistant_surgeon_ids: List[int] = []
    anesthesiologist_id: Optional[int] = None
    scrub_nurse_id: Optional[int] = None
    procedure_name: str
    icd_procedure_code: Optional[str] = None
    anesthesia_type: Optional[AnesthesiaType] = None
    surgery_type: Optional[str] = None
    pre_op_diagnosis: Optional[str] = None
    pre_op_notes: Optional[str] = None


class SurgeryUpdate(BaseModel):
    status: Optional[SurgeryStatus] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    intra_op_notes: Optional[str] = None
    complications: Optional[str] = None
    blood_loss_ml: Optional[int] = None
    fluids_given_ml: Optional[int] = None
    blood_transfusion_units: Optional[int] = None
    implants_used: Optional[str] = None
    specimens_sent: Optional[str] = None
    post_op_diagnosis: Optional[str] = None
    post_op_notes: Optional[str] = None
    post_op_instructions: Optional[str] = None
    post_op_condition: Optional[str] = None
    cancelled_reason: Optional[str] = None


class OTConsumableCreate(BaseModel):
    surgery_id: int
    item_name: str
    item_code: Optional[str] = None
    category: Optional[str] = None
    quantity_used: float
    unit: Optional[str] = None
    unit_cost: float = 0.0
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None


class OTConsumableResponse(BaseModel):
    id: int
    surgery_id: int
    item_name: str
    category: Optional[str]
    quantity_used: float
    unit: Optional[str]
    unit_cost: float
    total_cost: float
    batch_number: Optional[str]
    expiry_date: Optional[date]

    class Config:
        from_attributes = True


class SurgeryResponse(BaseModel):
    id: int
    surgery_number: str
    patient_id: int
    ot_id: int
    surgery_date: date
    scheduled_start_time: str
    scheduled_end_time: Optional[str]
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    duration_minutes: Optional[int]
    status: SurgeryStatus
    primary_surgeon_id: int
    procedure_name: str
    anesthesia_type: Optional[AnesthesiaType]
    pre_op_diagnosis: Optional[str]
    post_op_diagnosis: Optional[str]
    complications: Optional[str]
    consumables: List[OTConsumableResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ── Radiology ─────────────────────────────────────────
class RadiologyOrderCreate(BaseModel):
    patient_id: int
    ordered_by: int
    radiologist_id: Optional[int] = None
    scan_type: ScanType
    body_part: str
    clinical_indication: Optional[str] = None
    contrast_required: bool = False
    priority: str = "routine"
    opd_visit_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None
    price: float = 0.0


class RadiologyAssignRequest(BaseModel):
    """Assigns who performs the scan and on which equipment - roadmap's
    real RIS distinction between the technologist and the reporting
    radiologist."""
    performed_by: Optional[int] = None
    equipment_id: Optional[int] = None


class RadiologyReportSubmit(BaseModel):
    """Submitting a report only ever sets status to REPORTED - approval
    is a deliberately separate action (see RadiologyReportApprove) so
    the same call can't both write and approve a report."""
    findings: str
    impression: str
    recommendations: Optional[str] = None
    pacs_study_id: Optional[str] = None
    dicom_url: Optional[str] = None
    report_template_id: Optional[int] = None


class RadiologyCriticalFindingRequest(BaseModel):
    notes: str


class RadiologyReportUpdate(BaseModel):
    findings: Optional[str] = None
    impression: Optional[str] = None
    recommendations: Optional[str] = None
    status: Optional[ScanStatus] = None
    pacs_study_id: Optional[str] = None
    dicom_url: Optional[str] = None


class RadiologyImageResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    view_type: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RadiologyOrderResponse(BaseModel):
    id: int
    order_number: str
    patient_id: int
    ordered_by: int
    radiologist_id: Optional[int]
    performed_by: Optional[int]
    equipment_id: Optional[int]
    scan_type: ScanType
    body_part: str
    clinical_indication: Optional[str]
    contrast_required: bool
    priority: str
    status: ScanStatus
    scheduled_date: Optional[date]
    scheduled_time: Optional[str]
    performed_at: Optional[datetime]
    findings: Optional[str]
    impression: Optional[str]
    recommendations: Optional[str]
    reported_at: Optional[datetime]
    approved_at: Optional[datetime]
    report_template_id: Optional[int]
    is_critical_finding: bool
    critical_finding_notes: Optional[str]
    critical_finding_flagged_at: Optional[datetime]
    critical_finding_acknowledged_at: Optional[datetime]
    price: float
    images: List[RadiologyImageResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
