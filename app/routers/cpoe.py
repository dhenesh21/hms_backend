from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.cpoe import ClinicalOrder, OrderSet, ClinicalOrderNote, OrderType, OrderStatus
from app.models.emr import PatientAllergy
from app.models.user import User
from app.models.lab import LabOrder, LabOrderItem, LabTest
from app.models.radiology import RadiologyOrder
from app.models.pharmacy import DrugMaster
from app.models.patient import Patient
from app.models.cds import CDSRule, CDSAlertLog, CDSRuleType
from app.schemas.cpoe import (
    ClinicalOrderCreate, ClinicalOrderResponse, ClinicalOrderUpdate,
    OrderSetCreate, OrderSetResponse, OrderSetApply,
    OrderNoteCreate, OrderNoteResponse,
)

router = APIRouter(prefix="/cpoe", tags=["CPOE / Clinical Orders"])


def _run_safety_check(db: Session, patient_id: int, order_type: OrderType, item_name: str) -> Optional[dict]:
    """Allergy screen at order time (matches order text against active PatientAllergy rows)."""
    if order_type != OrderType.MEDICATION:
        return None
    allergies = db.query(PatientAllergy).filter(
        PatientAllergy.patient_id == patient_id,
        PatientAllergy.is_active == True
    ).all()
    hits = [a.allergen for a in allergies if a.allergen.lower() in item_name.lower()]
    if hits:
        return {"alert": "allergy_match", "matched_allergens": hits, "severity": "review_required"}
    return None


def _evaluate_cds_rules(db: Session, patient_id: int, order_type: OrderType, item_name: str) -> List[dict]:
    """
    Item 38/105 — configurable keyword-based CDS. NOT a licensed drug-interaction
    database (see models/cds.py docstring) — checks the hospital's own CDSRule
    table against this new order and, for interaction/duplicate-therapy rules,
    against the patient's other still-active medication orders.
    """
    if order_type != OrderType.MEDICATION:
        return []

    rules = db.query(CDSRule).filter(CDSRule.is_active == True).all()
    item_lower = item_name.lower()
    fired = []

    active_med_orders = db.query(ClinicalOrder).filter(
        ClinicalOrder.patient_id == patient_id,
        ClinicalOrder.order_type == OrderType.MEDICATION,
        ClinicalOrder.status.notin_([OrderStatus.CANCELLED, OrderStatus.COMPLETED]),
    ).all()

    for rule in rules:
        if rule.trigger_keyword.lower() not in item_lower:
            continue

        if rule.rule_type in (CDSRuleType.DRUG_INTERACTION, CDSRuleType.DUPLICATE_THERAPY):
            if not rule.conflict_keyword:
                continue
            conflict_hit = any(
                rule.conflict_keyword.lower() in o.item_name.lower() for o in active_med_orders
            )
            if conflict_hit:
                fired.append({"rule_id": rule.id, "severity": rule.severity.value, "message": rule.message})

        elif rule.rule_type == CDSRuleType.AGE_RESTRICTION:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if patient and patient.date_of_birth:
                age = (date.today() - patient.date_of_birth).days // 365
                if (rule.min_age is not None and age < rule.min_age) or \
                   (rule.max_age is not None and age > rule.max_age):
                    fired.append({"rule_id": rule.id, "severity": rule.severity.value, "message": rule.message})

        else:   # MAX_DOSE, GENERAL_ALERT — fires on keyword presence alone
            fired.append({"rule_id": rule.id, "severity": rule.severity.value, "message": rule.message})

    return fired


def _log_cds_alerts(db: Session, patient_id: int, order_id: int, alerts: List[dict]):
    for a in alerts:
        db.add(CDSAlertLog(
            rule_id=a.get("rule_id"), patient_id=patient_id, clinical_order_id=order_id,
            severity=a["severity"], message=a["message"],
        ))


# ── ORDER SETS ────────────────────────────────────────
@router.post("/order-sets", response_model=OrderSetResponse, status_code=201)
async def create_order_set(data: OrderSetCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    order_set = OrderSet(**data.model_dump(), created_by=current_user.id)
    db.add(order_set)
    db.commit()
    db.refresh(order_set)
    return order_set


@router.get("/order-sets", response_model=List[OrderSetResponse])
async def list_order_sets(specialty: Optional[str] = None, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    q = db.query(OrderSet).filter(OrderSet.is_active == True)
    if specialty:
        q = q.filter(OrderSet.specialty == specialty)
    return q.all()


@router.post("/order-sets/{order_set_id}/apply", response_model=List[ClinicalOrderResponse], status_code=201)
async def apply_order_set(order_set_id: int, data: OrderSetApply, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Explode an order set into individual ClinicalOrder rows for a patient."""
    order_set = db.query(OrderSet).filter(OrderSet.id == order_set_id).first()
    if not order_set:
        raise HTTPException(status_code=404, detail="Order set not found")

    created = []
    for item in order_set.items:
        order = ClinicalOrder(
            patient_id=data.patient_id,
            ordering_doctor_id=data.ordering_doctor_id,
            order_type=item.get("order_type", "other"),
            order_set_id=order_set_id,
            item_name=item.get("item_name", "Unnamed item"),
            instructions=item.get("instructions"),
            priority=item.get("default_priority", "routine"),
            source=data.source,
            source_id=data.source_id,
            ipd_admission_id=data.ipd_admission_id,
            safety_check_result=_run_safety_check(db, data.patient_id, item.get("order_type", "other"), item.get("item_name", "")),
        )
        db.add(order)
        created.append(order)
    db.commit()
    for o in created:
        db.refresh(o)
    return created


# ── CLINICAL ORDERS (CPOE) ─────────────────────────────
@router.post("/orders", response_model=ClinicalOrderResponse, status_code=201)
async def create_order(data: ClinicalOrderCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    safety_result = _run_safety_check(db, data.patient_id, data.order_type, data.item_name)
    cds_alerts = _evaluate_cds_rules(db, data.patient_id, data.order_type, data.item_name)

    combined = {}
    if safety_result:
        combined["allergy"] = safety_result
    if cds_alerts:
        combined["cds_alerts"] = cds_alerts

    order = ClinicalOrder(**data.model_dump(), safety_check_result=combined or None)
    db.add(order)
    db.flush()
    if cds_alerts:
        _log_cds_alerts(db, data.patient_id, order.id, cds_alerts)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=List[ClinicalOrderResponse])
async def list_orders(patient_id: Optional[int] = None, order_type: Optional[OrderType] = None,
                       status: Optional[OrderStatus] = None, ipd_admission_id: Optional[int] = None,
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(ClinicalOrder)
    if patient_id:
        q = q.filter(ClinicalOrder.patient_id == patient_id)
    if order_type:
        q = q.filter(ClinicalOrder.order_type == order_type)
    if status:
        q = q.filter(ClinicalOrder.status == status)
    if ipd_admission_id:
        q = q.filter(ClinicalOrder.ipd_admission_id == ipd_admission_id)
    return q.order_by(ClinicalOrder.created_at.desc()).all()


@router.get("/orders/queue/{order_type}", response_model=List[ClinicalOrderResponse])
async def department_queue(order_type: OrderType, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """Worklist for a downstream department (Lab / Pharmacy / Radiology / Nursing) to action."""
    priority_rank = case(
        (ClinicalOrder.priority == "stat", 0),
        (ClinicalOrder.priority == "urgent", 1),
        else_=2,
    )
    return db.query(ClinicalOrder).filter(
        ClinicalOrder.order_type == order_type,
        ClinicalOrder.status.in_([OrderStatus.ORDERED, OrderStatus.ACKNOWLEDGED, OrderStatus.IN_PROGRESS])
    ).order_by(priority_rank, ClinicalOrder.created_at.asc()).all()


@router.patch("/orders/{order_id}", response_model=ClinicalOrderResponse)
async def update_order(order_id: int, data: ClinicalOrderUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    order = db.query(ClinicalOrder).filter(ClinicalOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(order, k, v)

    if data.status == OrderStatus.ACKNOWLEDGED and not order.acknowledged_at:
        order.acknowledged_by = current_user.id
        order.acknowledged_at = datetime.now(timezone.utc)
    if data.status == OrderStatus.COMPLETED and not order.completed_at:
        order.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/notes", response_model=OrderNoteResponse, status_code=201)
async def add_order_note(order_id: int, data: OrderNoteCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    order = db.query(ClinicalOrder).filter(ClinicalOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    note = ClinicalOrderNote(order_id=order_id, note=data.note, author_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/orders/{order_id}/notes", response_model=List[OrderNoteResponse])
async def get_order_notes(order_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return db.query(ClinicalOrderNote).filter(ClinicalOrderNote.order_id == order_id).all()


# ── CLAIM: pull a CPOE order into the executing department's own module ──
# These create the real downstream record (LabOrder / RadiologyOrder) so the
# department works from its normal screens, while keeping the CPOE order as
# the source-of-truth audit trail via fulfilled_module / fulfilled_ref_id.

def _order_or_404(db: Session, order_id: int) -> ClinicalOrder:
    order = db.query(ClinicalOrder).filter(ClinicalOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Clinical order not found")
    if order.fulfilled_ref_id:
        raise HTTPException(status_code=400, detail="Order has already been claimed")
    return order


@router.post("/orders/{order_id}/claim/lab", response_model=ClinicalOrderResponse)
async def claim_into_lab(order_id: int, test_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    order = _order_or_404(db, order_id)
    if order.order_type != OrderType.LAB:
        raise HTTPException(status_code=400, detail="Order is not a lab order")
    test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found — pass the matching test_id")

    count = db.query(LabOrder).count() + 1
    lab_order = LabOrder(
        order_number=f"LAB{count:07d}",
        patient_id=order.patient_id,
        ordered_by=order.ordering_doctor_id,
        priority=order.priority,
        ipd_admission_id=order.ipd_admission_id,
        clinical_info=order.instructions,
    )
    db.add(lab_order)
    db.flush()
    db.add(LabOrderItem(order_id=lab_order.id, test_id=test_id))

    order.fulfilled_module = "lab_order"
    order.fulfilled_ref_id = lab_order.id
    order.status = OrderStatus.IN_PROGRESS
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/claim/radiology", response_model=ClinicalOrderResponse)
async def claim_into_radiology(order_id: int, scan_type: str, body_part: str,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    order = _order_or_404(db, order_id)
    if order.order_type != OrderType.RADIOLOGY:
        raise HTTPException(status_code=400, detail="Order is not a radiology order")

    count = db.query(RadiologyOrder).count() + 1
    rad_order = RadiologyOrder(
        order_number=f"RAD{count:07d}",
        patient_id=order.patient_id,
        ordered_by=order.ordering_doctor_id,
        scan_type=scan_type,
        body_part=body_part,
        clinical_indication=order.instructions,
        priority=order.priority.value if hasattr(order.priority, "value") else order.priority,
        ipd_admission_id=order.ipd_admission_id,
    )
    db.add(rad_order)
    db.flush()

    order.fulfilled_module = "radiology_order"
    order.fulfilled_ref_id = rad_order.id
    order.status = OrderStatus.IN_PROGRESS
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/claim/pharmacy", response_model=ClinicalOrderResponse)
async def claim_into_pharmacy(order_id: int, drug_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """
    Links the CPOE order to the matching DrugMaster entry so the pharmacist finds it
    on their worklist. Deliberately does NOT auto-create the PharmacyDispense/batch
    deduction — that needs the pharmacist to pick a stock batch (FEFO/expiry-aware),
    which stays a manual step via the existing POST /pharmacy/dispense endpoint.
    """
    order = _order_or_404(db, order_id)
    if order.order_type != OrderType.MEDICATION:
        raise HTTPException(status_code=400, detail="Order is not a medication order")
    drug = db.query(DrugMaster).filter(DrugMaster.id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found in drug master")

    order.fulfilled_module = "drug_master"
    order.fulfilled_ref_id = drug.id
    order.status = OrderStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(order)
    return order
