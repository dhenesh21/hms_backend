from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.preventive_health import HealthCheckupBooking, CheckupBookingStatus
from app.models.billing import BillingPackage
from app.models.emr import ImmunizationRecord
from app.models.user import User
from app.schemas.preventive_health import (
    CheckupBookingCreate, CheckupBookingUpdateStatus, CheckupBookingReview, CheckupBookingResponse,
)

router = APIRouter(prefix="/preventive-health", tags=["Preventive Healthcare / Health Check-ups"])


@router.post("/checkup-bookings", response_model=CheckupBookingResponse, status_code=201)
async def book_checkup(data: CheckupBookingCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    package = db.query(BillingPackage).filter(
        BillingPackage.id == data.package_id, BillingPackage.is_active == True).first()
    if not package:
        raise HTTPException(status_code=404, detail="Health package not found or inactive")
    booking = HealthCheckupBooking(**data.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/checkup-bookings", response_model=List[CheckupBookingResponse])
async def list_bookings(patient_id: Optional[int] = None, status: Optional[CheckupBookingStatus] = None,
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(HealthCheckupBooking)
    if patient_id:
        q = q.filter(HealthCheckupBooking.patient_id == patient_id)
    if status:
        q = q.filter(HealthCheckupBooking.status == status)
    return q.order_by(HealthCheckupBooking.scheduled_date.desc()).all()


@router.patch("/checkup-bookings/{booking_id}/status", response_model=CheckupBookingResponse)
async def update_booking_status(booking_id: int, data: CheckupBookingUpdateStatus, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    booking = db.query(HealthCheckupBooking).filter(HealthCheckupBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(booking, k, v)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/checkup-bookings/{booking_id}/review", response_model=CheckupBookingResponse)
async def add_review(booking_id: int, data: CheckupBookingReview, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    booking = db.query(HealthCheckupBooking).filter(HealthCheckupBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.findings_summary = data.findings_summary
    booking.recommendations = data.recommendations
    booking.reviewed_by = data.reviewed_by
    booking.status = CheckupBookingStatus.REPORT_READY
    db.commit()
    db.refresh(booking)
    return booking


# ── Vaccination / Immunization due-list (item 195) ─────
# ImmunizationRecord + its create/list-by-patient endpoints already exist in
# routers/emr.py. The one thing missing was a hospital-wide "who's due" view,
# added here rather than duplicating the existing record CRUD.
@router.get("/vaccinations/due-soon")
async def vaccinations_due_soon(within_days: int = 30, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    cutoff = date.today() + timedelta(days=within_days)
    records = db.query(ImmunizationRecord).filter(
        ImmunizationRecord.next_due_date.isnot(None),
        ImmunizationRecord.next_due_date <= cutoff,
        ImmunizationRecord.next_due_date >= date.today(),
    ).order_by(ImmunizationRecord.next_due_date).all()
    return [
        {"patient_id": r.patient_id, "vaccine_name": r.vaccine_name,
         "dose_number": r.dose_number, "next_due_date": r.next_due_date}
        for r in records
    ]
