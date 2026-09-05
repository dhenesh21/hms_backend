from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.emr import DiagnosisRecord, PatientAllergy, ChronicCondition, MedicationHistory
from app.models.cpoe import ClinicalOrder, OrderStatus
from app.models.care_plan import PatientCarePlan, PathwayStatus
from app.models.clinical_forms import FormSubmission
from app.models.consent import PatientConsent
from app.models.lab import LabOrderItem, LabOrder, LabTest
from app.models.doctor import DoctorProfile
from app.schemas.clinical_timeline import TimelineEvent, CriticalResultAlert, PatientSummary

router = APIRouter(prefix="/clinical-timeline", tags=["Clinical Timeline"])


@router.get("/patient/{patient_id}", response_model=List[TimelineEvent])
async def get_patient_timeline(patient_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    """
    Read-only merge of everything clinically relevant for a patient, sorted newest
    first. Pulls from existing tables — no new storage. Item 29 on the checklist.
    """
    events: List[TimelineEvent] = []

    for d in db.query(DiagnosisRecord).filter(DiagnosisRecord.patient_id == patient_id).all():
        events.append(TimelineEvent(
            event_time=d.created_at, event_type="diagnosis", category=d.diagnosis_type,
            title=d.diagnosis, detail=d.icd_code, ref_id=d.id,
        ))

    for o in db.query(ClinicalOrder).filter(ClinicalOrder.patient_id == patient_id).all():
        events.append(TimelineEvent(
            event_time=o.created_at, event_type="order", category=o.order_type.value,
            title=f"{o.item_name} ({o.status.value})", detail=o.instructions, ref_id=o.id,
        ))

    for f in db.query(FormSubmission).filter(FormSubmission.patient_id == patient_id).all():
        events.append(TimelineEvent(
            event_time=f.created_at, event_type="form", title=f"Form submission #{f.template_id}",
            ref_id=f.id,
        ))

    for c in db.query(PatientConsent).filter(PatientConsent.patient_id == patient_id).all():
        events.append(TimelineEvent(
            event_time=c.created_at, event_type="consent", category=c.status.value,
            title=f"Consent ({c.status.value})", ref_id=c.id,
        ))

    # Critical / abnormal lab results surface as flagged timeline entries
    critical_items = (
        db.query(LabOrderItem, LabTest)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .join(LabTest, LabOrderItem.test_id == LabTest.id)
        .filter(LabOrder.patient_id == patient_id, LabOrderItem.result_status == "critical")
        .all()
    )
    for item, test in critical_items:
        events.append(TimelineEvent(
            event_time=item.result_entered_at or item.created_at,
            event_type="critical_result", category="lab",
            title=f"CRITICAL: {test.test_name} = {item.result_value or item.result_numeric}",
            is_critical=True, ref_id=item.id,
        ))

    events.sort(key=lambda e: e.event_time, reverse=True)
    return events


@router.get("/critical-results", response_model=List[CriticalResultAlert])
async def get_open_critical_results(db: Session = Depends(get_db),
                                     current_user: User = Depends(get_current_user)):
    """
    Hospital-wide worklist of critical lab results awaiting acknowledgement — item 91.
    Note: this currently reads whatever Lab has already flagged result_status='critical'
    at result entry; it does not yet push a real-time alert (SMS/app push) to the
    ordering doctor — that's the documented follow-up once a delivery channel is chosen.
    """
    rows = (
        db.query(LabOrderItem, LabTest, LabOrder)
        .join(LabTest, LabOrderItem.test_id == LabTest.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .filter(LabOrderItem.result_status == "critical", LabOrderItem.approved_at.is_(None))
        .all()
    )
    return [
        CriticalResultAlert(
            patient_id=order.patient_id,
            lab_order_item_id=item.id,
            test_name=test.test_name,
            result_value=item.result_value,
            result_status=item.result_status,
            reported_at=item.result_entered_at,
        )
        for item, test, order in rows
    ]


@router.post("/critical-results/{lab_order_item_id}/notify-doctor")
async def notify_doctor_of_critical_result(lab_order_item_id: int, db: Session = Depends(get_db),
                                            current_user: User = Depends(get_current_user)):
    """
    Item 91 — real push, not just visibility. Emails the ordering doctor
    immediately. Staff-triggered (a nurse/lab tech clicks "notify doctor" from
    the critical-results worklist) rather than automatic-on-result-entry —
    wiring this into Lab's own result-save endpoint so it fires automatically
    the moment a critical value is entered is the natural next step, and would
    need a change inside routers/lab.py itself (outside this module's files).
    SMS uses the same send_sms() helper already used for patient notifications,
    just pointed at the doctor's phone via their User record if present.
    """
    from app.routers.notify import send_email, send_sms, HOSPITAL_NAME

    item = db.query(LabOrderItem).filter(LabOrderItem.id == lab_order_item_id).first()
    if not item:
        return {"error": "Lab result item not found"}
    order = db.query(LabOrder).filter(LabOrder.id == item.order_id).first()
    test = db.query(LabTest).filter(LabTest.id == item.test_id).first()
    doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.id == order.ordered_by).first() if order else None
    doctor_user = db.query(User).filter(User.id == doctor_profile.user_id).first() if doctor_profile else None

    if not doctor_user:
        return {"error": "Could not resolve the ordering doctor's account for this result"}

    subject = f"URGENT — Critical Lab Result — {HOSPITAL_NAME}"
    body = (f"Critical result for Patient #{order.patient_id}: {test.test_name} = "
            f"{item.result_value or item.result_numeric}. Order {order.order_number}. "
            f"Please review immediately.")
    results = {"email": False, "sms": False}
    if doctor_user.email:
        html = f"<div style='font-family:Arial,sans-serif;padding:20px'><h2 style='color:#DC2626'>Critical Result Alert</h2><p>{body}</p></div>"
        results["email"] = await send_email(doctor_user.email, subject, html)
    if getattr(doctor_user, "phone", None):
        results["sms"] = await send_sms(doctor_user.phone, body)

    return {"message": "Doctor notified", "doctor": doctor_user.full_name, "results": results}


@router.get("/patient/{patient_id}/summary", response_model=PatientSummary)
async def get_patient_summary(patient_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """
    Items 233/234 — the "current state" consolidated view, complementing the
    chronological /patient/{id} timeline above. Pure aggregation over
    existing EMR/CPOE/Care Plan tables, no new storage.
    """
    allergies = db.query(PatientAllergy).filter(
        PatientAllergy.patient_id == patient_id, PatientAllergy.is_active == True).all()
    conditions = db.query(ChronicCondition).filter(
        ChronicCondition.patient_id == patient_id, ChronicCondition.is_active == True).all()
    medications = db.query(MedicationHistory).filter(
        MedicationHistory.patient_id == patient_id, MedicationHistory.is_current == True).all()
    care_plans = db.query(PatientCarePlan).filter(
        PatientCarePlan.patient_id == patient_id, PatientCarePlan.status == PathwayStatus.ACTIVE).all()
    open_orders = db.query(ClinicalOrder).filter(
        ClinicalOrder.patient_id == patient_id,
        ClinicalOrder.status.notin_([OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
    ).all()

    return PatientSummary(
        patient_id=patient_id,
        active_allergies=[{"allergen": a.allergen, "severity": a.severity.value if a.severity else None} for a in allergies],
        active_chronic_conditions=[{"condition": c.condition_name, "status": c.current_status} for c in conditions],
        current_medications=[{"drug": m.drug_name, "dosage": m.dosage, "frequency": m.frequency} for m in medications],
        active_care_plans=[{"id": p.id, "title": p.title} for p in care_plans],
        open_clinical_orders=[{"id": o.id, "type": o.order_type.value, "item": o.item_name, "status": o.status.value} for o in open_orders],
        generated_at=datetime.now(timezone.utc),
    )
