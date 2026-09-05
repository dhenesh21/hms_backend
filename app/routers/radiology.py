from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date as dt_date
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.radiology import RadiologyOrder, RadiologyImage, ScanStatus, ScanType
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.schemas.ot_radiology import (
    RadiologyOrderCreate,
    RadiologyOrderResponse, RadiologyImageResponse,
    RadiologyAssignRequest, RadiologyReportSubmit, RadiologyCriticalFindingRequest,
)

router = APIRouter(prefix="/radiology", tags=["Radiology"])

# Real RIS status state machine - previously update_status accepted any
# ScanStatus value with zero validation, so an order could jump straight
# from ORDERED to APPROVED (skipping the scan and report entirely) or
# move backwards from REPORTED to SCHEDULED. This is what a real RIS
# workflow enforces: each step can only follow specific prior steps.
ALLOWED_TRANSITIONS = {
    ScanStatus.ORDERED: {ScanStatus.SCHEDULED, ScanStatus.CANCELLED},
    ScanStatus.SCHEDULED: {ScanStatus.PATIENT_ARRIVED, ScanStatus.CANCELLED},
    ScanStatus.PATIENT_ARRIVED: {ScanStatus.IN_PROGRESS, ScanStatus.CANCELLED},
    ScanStatus.IN_PROGRESS: {ScanStatus.IMAGES_UPLOADED, ScanStatus.CANCELLED},
    ScanStatus.IMAGES_UPLOADED: {ScanStatus.REPORT_PENDING, ScanStatus.CANCELLED},
    ScanStatus.REPORT_PENDING: {ScanStatus.REPORTED, ScanStatus.CANCELLED},
    # REPORTED -> APPROVED only via the dedicated /approve endpoint, not
    # via the generic status setter, so approval always goes through its
    # own explicit action (see approve_report below).
    ScanStatus.REPORTED: set(),
    ScanStatus.APPROVED: set(),   # terminal
    ScanStatus.CANCELLED: set(),  # terminal
}


@router.post("/orders", response_model=RadiologyOrderResponse, status_code=201)
async def create_radiology_order(data: RadiologyOrderCreate,
                                  db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    from sqlalchemy.exc import IntegrityError

    order_data = data.model_dump()
    attempt_base = next_sequence_number(db, RadiologyOrder)
    order = None
    last_error = None
    for i in range(MAX_RETRIES):
        order_data["order_number"] = f"RAD{attempt_base + i:07d}"
        order = RadiologyOrder(**order_data)
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

    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=list[RadiologyOrderResponse])
async def list_orders(patient_id: Optional[int] = Query(None),
                      scan_type: Optional[ScanType] = Query(None),
                      status: Optional[ScanStatus] = Query(None),
                      scheduled_date: Optional[dt_date] = Query(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    query = db.query(RadiologyOrder)
    if patient_id:
        query = query.filter(RadiologyOrder.patient_id == patient_id)
    if scan_type:
        query = query.filter(RadiologyOrder.scan_type == scan_type)
    if status:
        query = query.filter(RadiologyOrder.status == status)
    if scheduled_date:
        query = query.filter(RadiologyOrder.scheduled_date == scheduled_date)
    return query.order_by(RadiologyOrder.created_at.desc()).limit(100).all()


@router.get("/orders/critical", response_model=list[RadiologyOrderResponse])
async def list_critical_findings(unacknowledged_only: bool = Query(True),
                                 db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    """Queryable worklist of flagged critical findings - the whole point
    of making this a real field instead of free text buried in a report.
    Registered before /orders/{order_id} so FastAPI's path matching
    doesn't try to parse 'critical' as an integer order_id."""
    q = db.query(RadiologyOrder).filter(RadiologyOrder.is_critical_finding == True)  # noqa: E712
    if unacknowledged_only:
        q = q.filter(RadiologyOrder.critical_finding_acknowledged_at.is_(None))
    return q.order_by(RadiologyOrder.critical_finding_flagged_at.desc()).all()


@router.get("/orders/{order_id}", response_model=RadiologyOrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/orders/{order_id}/status")
async def update_status(order_id: int, status: ScanStatus,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from '{order.status.value}' to '{status.value}'. Allowed next steps: {[s.value for s in allowed] or 'none (terminal status)'}",
        )

    order.status = status
    if status == ScanStatus.IN_PROGRESS:
        order.performed_at = datetime.utcnow()
    db.commit()
    return {"message": f"Status updated to {status.value}"}


@router.put("/orders/{order_id}/assign", response_model=RadiologyOrderResponse)
async def assign_technologist_and_equipment(order_id: int, data: RadiologyAssignRequest,
                                             db: Session = Depends(get_db),
                                             current_user: User = Depends(get_current_user)):
    """Records who operates the equipment and which machine performs the
    study - a real RIS distinction from the radiologist who later
    reports on the images."""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if data.performed_by is not None:
        order.performed_by = data.performed_by
    if data.equipment_id is not None:
        order.equipment_id = data.equipment_id
    db.commit()
    db.refresh(order)
    return order


@router.put("/orders/{order_id}/report", response_model=RadiologyOrderResponse)
async def submit_report(order_id: int, data: RadiologyReportSubmit,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """Submitting a report only ever transitions to REPORTED - it cannot
    also approve in the same call (see /approve), so writing a report
    and approving it are always two distinct, separately-accountable
    actions."""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (ScanStatus.IMAGES_UPLOADED, ScanStatus.REPORT_PENDING):
        raise HTTPException(status_code=400, detail=f"Cannot submit a report from status '{order.status.value}'")

    order.findings = data.findings
    order.impression = data.impression
    order.recommendations = data.recommendations
    if data.pacs_study_id:
        order.pacs_study_id = data.pacs_study_id
    if data.dicom_url:
        order.dicom_url = data.dicom_url
    if data.report_template_id:
        template = db.query(ReportTemplate).filter(ReportTemplate.id == data.report_template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Report template not found")
        order.report_template_id = data.report_template_id
    order.status = ScanStatus.REPORTED
    order.reported_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return order


@router.put("/orders/{order_id}/approve", response_model=RadiologyOrderResponse)
async def approve_report(order_id: int,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Approval is its own explicit action requiring the order already
    be in REPORTED status - previously the generic status setter let a
    single call both write and approve a report with no separation of
    duties at all."""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != ScanStatus.REPORTED:
        raise HTTPException(status_code=400, detail="Only a reported study can be approved")

    order.status = ScanStatus.APPROVED
    order.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


@router.put("/orders/{order_id}/flag-critical", response_model=RadiologyOrderResponse)
async def flag_critical_finding(order_id: int, data: RadiologyCriticalFindingRequest,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    """Flags a study as needing urgent attention from the ordering
    doctor - roadmap's real RIS requirement that this be a trackable,
    queryable flag rather than something buried in free-text impression
    that nobody can query on or be alerted about."""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.is_critical_finding = True
    order.critical_finding_notes = data.notes
    order.critical_finding_flagged_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


@router.put("/orders/{order_id}/acknowledge-critical", response_model=RadiologyOrderResponse)
async def acknowledge_critical_finding(order_id: int,
                                       db: Session = Depends(get_db),
                                       current_user: User = Depends(get_current_user)):
    """The ordering doctor (or covering clinician) acknowledges having
    seen a critical finding - closes the loop on the escalation."""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.is_critical_finding:
        raise HTTPException(status_code=400, detail="This order has no critical finding flagged")
    if order.critical_finding_acknowledged_at:
        raise HTTPException(status_code=400, detail="Critical finding already acknowledged")

    order.critical_finding_acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/images")
async def upload_image_record(order_id: int, file_name: str,
                               file_path: str, view_type: Optional[str] = None,
                               db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    image = RadiologyImage(
        order_id=order_id, file_name=file_name,
        file_path=file_path, view_type=view_type,
        uploaded_by=current_user.id
    )
    db.add(image)

    if order.status in [ScanStatus.IN_PROGRESS, ScanStatus.PATIENT_ARRIVED]:
        order.status = ScanStatus.IMAGES_UPLOADED
        if not order.performed_at:
            order.performed_at = datetime.utcnow()

    db.commit()
    db.refresh(image)
    return {"message": "Image record added", "image_id": image.id}


@router.get("/pending")
async def get_pending_reports(db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    orders = db.query(RadiologyOrder).filter(
        RadiologyOrder.status.in_([
            ScanStatus.ORDERED, ScanStatus.SCHEDULED,
            ScanStatus.IMAGES_UPLOADED, ScanStatus.REPORT_PENDING
        ])
    ).order_by(RadiologyOrder.created_at.asc()).all()
    return [{
        "id": o.id, "order_number": o.order_number,
        "patient_id": o.patient_id,
        "scan_type": o.scan_type, "body_part": o.body_part,
        "priority": o.priority, "status": o.status,
        "scheduled_date": o.scheduled_date,
        "image_count": len(o.images)
    } for o in orders]


@router.get("/dashboard/stats")
async def radiology_stats(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    from datetime import date
    from sqlalchemy import func, Date
    today = date.today()
    today_orders = db.query(RadiologyOrder).filter(
        func.cast(RadiologyOrder.created_at, Date) == today).count()
    pending_report = db.query(RadiologyOrder).filter(
        RadiologyOrder.status.in_([ScanStatus.IMAGES_UPLOADED, ScanStatus.REPORT_PENDING])).count()
    reported_today = db.query(RadiologyOrder).filter(
        func.cast(RadiologyOrder.reported_at, Date) == today).count()
    by_type = db.query(RadiologyOrder.scan_type, func.count(RadiologyOrder.id)).group_by(
        RadiologyOrder.scan_type).all()
    return {
        "today_orders": today_orders,
        "pending_reports": pending_report,
        "reported_today": reported_today,
        "by_scan_type": {str(t): c for t, c in by_type}
    }




