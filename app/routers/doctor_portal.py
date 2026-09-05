from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.appointment import Appointment
from app.models.opd import OPDVisit
from app.models.cpoe import ClinicalOrder, OrderStatus
from app.models.care_plan import PatientCarePlan, PathwayStatus
from app.schemas.doctor_portal import (
    TodayAppointmentResponse, PendingOrderResponse, MyCarePlanResponse,
)

router = APIRouter(prefix="/doctor-portal", tags=["Doctor Portal"])


def _require_doctor_profile(db: Session, current_user: User) -> DoctorProfile:
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Doctor portal is for doctor accounts only")
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No doctor profile linked to this account")
    return profile


@router.get("/today-appointments", response_model=List[TodayAppointmentResponse])
async def today_appointments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doctor = _require_doctor_profile(db, current_user)
    return db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id, Appointment.appointment_date == date.today()
    ).order_by(Appointment.appointment_date).all()


@router.get("/my-patients", response_model=List[int])
async def my_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Distinct patient IDs this doctor has an OPD visit history with."""
    doctor = _require_doctor_profile(db, current_user)
    rows = db.query(OPDVisit.patient_id).filter(OPDVisit.doctor_id == doctor.id).distinct().all()
    return [r[0] for r in rows]


@router.get("/pending-orders", response_model=List[PendingOrderResponse])
async def pending_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """CPOE orders this doctor raised that haven't completed yet — a personal worklist."""
    doctor = _require_doctor_profile(db, current_user)
    orders = db.query(ClinicalOrder).filter(
        ClinicalOrder.ordering_doctor_id == doctor.id,
        ClinicalOrder.status.notin_([OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
    ).order_by(ClinicalOrder.created_at.desc()).all()
    return [
        PendingOrderResponse(
            id=o.id, patient_id=o.patient_id, order_type=o.order_type.value,
            item_name=o.item_name, status=o.status.value, created_at=o.created_at,
        ) for o in orders
    ]


@router.get("/my-active-care-plans", response_model=List[MyCarePlanResponse])
async def my_active_care_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_doctor_profile(db, current_user)
    plans = db.query(PatientCarePlan).filter(
        PatientCarePlan.created_by == current_user.id, PatientCarePlan.status == PathwayStatus.ACTIVE
    ).all()
    return [
        MyCarePlanResponse(id=p.id, patient_id=p.patient_id, title=p.title,
                            status=p.status.value, started_at=p.started_at)
        for p in plans
    ]
