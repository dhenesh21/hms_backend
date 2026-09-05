from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.lab import LabTest, LabOrder, LabOrderItem, LabSubResult, SampleStatus
from app.models.user import User
from app.schemas.lab import (
    LabTestCreate, LabTestResponse,
    LabOrderCreate, LabOrderResponse,
    LabResultEntry, LabOrderItemResponse,
    SampleCollectionUpdate
)

router = APIRouter(prefix="/lab", tags=["Laboratory"])


# ── LAB TESTS MASTER ──────────────────────────────────
@router.post("/tests", response_model=LabTestResponse, status_code=201)
async def create_lab_test(data: LabTestCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    existing = db.query(LabTest).filter(LabTest.test_code == data.test_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Test code already exists")
    test = LabTest(**data.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/tests", response_model=list[LabTestResponse])
async def list_lab_tests(category: Optional[str] = Query(None),
                         search: Optional[str] = Query(None),
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    query = db.query(LabTest).filter(LabTest.is_active == True)
    if category:
        query = query.filter(LabTest.category == category)
    if search:
        query = query.filter(LabTest.test_name.ilike(f"%{search}%"))
    return query.order_by(LabTest.test_name).all()


# ── LAB ORDERS ────────────────────────────────────────
@router.post("/orders", response_model=LabOrderResponse, status_code=201)
async def create_lab_order(data: LabOrderCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    if not data.test_ids:
        raise HTTPException(status_code=400, detail="At least one test required")

    from sqlalchemy.exc import IntegrityError

    attempt_base = next_sequence_number(db, LabOrder)
    order = None
    last_error = None
    for i in range(MAX_RETRIES):
        order = LabOrder(
            order_number=f"LAB{attempt_base + i:07d}",
            patient_id=data.patient_id,
            ordered_by=data.ordered_by,
            priority=data.priority,
            opd_visit_id=data.opd_visit_id,
            ipd_admission_id=data.ipd_admission_id,
            clinical_info=data.clinical_info
        )
        db.add(order)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            order = None
    if last_error:
        raise last_error

    for test_id in data.test_ids:
        test = db.query(LabTest).filter(LabTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
        item = LabOrderItem(order_id=order.id, test_id=test_id)
        db.add(item)

    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=list[LabOrderResponse])
async def list_orders(patient_id: Optional[int] = Query(None),
                      status: Optional[SampleStatus] = Query(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    query = db.query(LabOrder).filter(LabOrder.is_active == True)
    if patient_id:
        query = query.filter(LabOrder.patient_id == patient_id)
    if status:
        query = query.join(LabOrderItem).filter(LabOrderItem.status == status)
    return query.order_by(LabOrder.ordered_at.desc()).limit(100).all()


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ── SAMPLE COLLECTION ─────────────────────────────────
@router.post("/sample-collection")
async def collect_samples(data: SampleCollectionUpdate,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    updated = []
    for item_id in data.order_item_ids:
        item = db.query(LabOrderItem).filter(LabOrderItem.id == item_id).first()
        if not item:
            continue
        barcode = f"{data.barcode_prefix or 'LAB'}{item_id:06d}"
        item.barcode = barcode
        item.status = SampleStatus.SAMPLE_COLLECTED
        item.sample_collected_at = datetime.utcnow()
        item.sample_collected_by = current_user.id
        updated.append({"item_id": item_id, "barcode": barcode})
    db.commit()
    return {"collected": len(updated), "items": updated}


@router.put("/sample-received/{item_id}")
async def receive_sample(item_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    item = db.query(LabOrderItem).filter(LabOrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    item.status = SampleStatus.SAMPLE_RECEIVED
    item.sample_received_at = datetime.utcnow()
    item.sample_received_by = current_user.id
    db.commit()
    return {"message": "Sample received", "barcode": item.barcode}


# ── RESULT ENTRY ──────────────────────────────────────
@router.post("/results")
async def enter_result(data: LabResultEntry, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    item = db.query(LabOrderItem).filter(LabOrderItem.id == data.order_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    item.result_value = data.result_value
    item.result_numeric = data.result_numeric
    item.result_unit = data.result_unit
    item.result_status = data.result_status
    item.normal_range = data.normal_range
    item.remarks = data.remarks
    item.status = SampleStatus.RESULT_ENTERED
    item.result_entered_at = datetime.utcnow()
    item.result_entered_by = current_user.id

    # Sub-results for panel tests
    for sub in data.sub_results:
        sub_result = LabSubResult(order_item_id=item.id, **sub.model_dump())
        db.add(sub_result)

    db.commit()

    # Item 91 (Critical Result Management) — automatic push, not just
    # visibility. Fires the moment a critical value is entered, using the
    # same email/SMS helper the staff-triggered notify-doctor button in
    # Clinical Timeline uses. Failure to notify (bad email config, doctor
    # has no email on file, etc) must never block the result from saving —
    # the result is already committed above; notification is best-effort.
    if item.result_status == "critical":
        try:
            from app.routers.notify import send_email, send_sms, HOSPITAL_NAME
            order = db.query(LabOrder).filter(LabOrder.id == item.order_id).first()
            test = db.query(LabTest).filter(LabTest.id == item.test_id).first()
            doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.id == order.ordered_by).first() if order else None
            doctor_user = db.query(User).filter(User.id == doctor_profile.user_id).first() if doctor_profile else None
            if doctor_user:
                subject = f"URGENT — Critical Lab Result — {HOSPITAL_NAME}"
                body = (f"Critical result for Patient #{order.patient_id}: {test.test_name} = "
                        f"{item.result_value or item.result_numeric}. Order {order.order_number}. "
                        f"Please review immediately.")
                if doctor_user.email:
                    html = f"<div style='font-family:Arial,sans-serif;padding:20px'><h2 style='color:#DC2626'>Critical Result Alert</h2><p>{body}</p></div>"
                    await send_email(doctor_user.email, subject, html)
                if doctor_user.phone:
                    await send_sms(doctor_user.phone, body)
        except Exception:
            pass  # never let a notification failure block a saved result

    return {"message": "Result entered successfully"}


# ── RESULT APPROVAL ───────────────────────────────────
@router.put("/approve/{item_id}")
async def approve_result(item_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    item = db.query(LabOrderItem).filter(LabOrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    if item.status != SampleStatus.RESULT_ENTERED:
        raise HTTPException(status_code=400, detail="Result not yet entered")

    from app.models.doctor import DoctorProfile
    doctor = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    item.status = SampleStatus.APPROVED
    item.approved_at = datetime.utcnow()
    item.approved_by = doctor.id if doctor else None
    db.commit()
    return {"message": "Result approved"}


@router.put("/reject/{item_id}")
async def reject_sample(item_id: int, reason: str,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    item = db.query(LabOrderItem).filter(LabOrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    item.status = SampleStatus.REJECTED
    item.reject_reason = reason
    db.commit()
    return {"message": "Sample rejected"}


# ── PENDING TESTS ─────────────────────────────────────
@router.get("/pending")
async def get_pending(db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    items = db.query(LabOrderItem).filter(
        LabOrderItem.status.in_([
            SampleStatus.ORDERED, SampleStatus.SAMPLE_COLLECTED,
            SampleStatus.SAMPLE_RECEIVED, SampleStatus.PROCESSING,
            SampleStatus.RESULT_ENTERED
        ])
    ).all()
    return [{
        "id": i.id, "order_id": i.order_id,
        "order_number": i.order.order_number if i.order else None,
        "patient_id": i.order.patient_id if i.order else None,
        "test_name": i.test.test_name if i.test else None,
        "test_code": i.test.test_code if i.test else None,
        "status": i.status, "barcode": i.barcode,
        "priority": i.order.priority if i.order else None,
        "ordered_at": i.created_at
    } for i in items]


# ── DASHBOARD STATS ───────────────────────────────────
@router.get("/dashboard/stats")
async def lab_stats(db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    from datetime import date
    from sqlalchemy import func, Date
    today_orders = db.query(LabOrder).filter(
        func.cast(LabOrder.ordered_at, Date) == date.today()).count()
    pending = db.query(LabOrderItem).filter(
        LabOrderItem.status.in_([SampleStatus.ORDERED, SampleStatus.SAMPLE_COLLECTED,
                                  SampleStatus.SAMPLE_RECEIVED, SampleStatus.PROCESSING])).count()
    result_pending_approval = db.query(LabOrderItem).filter(
        LabOrderItem.status == SampleStatus.RESULT_ENTERED).count()
    approved_today = db.query(LabOrderItem).filter(
        LabOrderItem.status == SampleStatus.APPROVED,
        func.cast(LabOrderItem.approved_at, Date) == date.today()).count()
    return {
        "today_orders": today_orders,
        "pending_collection": pending,
        "pending_approval": result_pending_approval,
        "approved_today": approved_today
    }




