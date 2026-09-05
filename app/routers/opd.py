from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.opd import OPDVisit, Prescription
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User, UserRole
from app.schemas.opd import OPDVisitCreate, OPDVisitUpdate, OPDVisitResponse

router = APIRouter(prefix="/opd", tags=["OPD"])


def calc_bmi(weight_kg, height_cm):
    if weight_kg and height_cm and height_cm > 0:
        return round(weight_kg / ((height_cm / 100) ** 2), 2)
    return None


@router.post("/visits", response_model=OPDVisitResponse, status_code=201)
async def create_opd_visit(
    data: OPDVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prescriptions_data = data.prescriptions
    visit_data = data.model_dump(exclude={"prescriptions"})
    visit_data["bmi"] = calc_bmi(visit_data.get("weight_kg"), visit_data.get("height_cm"))
    visit_data["created_by"] = current_user.id

    # visit_number generation is retried on collision: two OPD desks can
    # register a visit in the same instant and race for the same count.
    attempt_base = next_sequence_number(db, OPDVisit)
    visit = None
    last_error = None
    for i in range(MAX_RETRIES):
        visit_data["visit_number"] = f"OPD{attempt_base + i:07d}"
        visit = OPDVisit(**visit_data)
        db.add(visit)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            visit = None
    if last_error:
        raise last_error

    # Add prescriptions
    for p in prescriptions_data:
        prescription = Prescription(**p.model_dump(), opd_visit_id=visit.id)
        db.add(prescription)

    # Update appointment status if linked
    if data.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
        if appt:
            appt.status = AppointmentStatus.IN_PROGRESS

    db.commit()
    db.refresh(visit)
    return visit


@router.get("/visits", response_model=list[OPDVisitResponse])
async def list_opd_visits(
    patient_id: Optional[int] = Query(None),
    doctor_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(OPDVisit)
    if patient_id:
        query = query.filter(OPDVisit.patient_id == patient_id)
    if doctor_id:
        query = query.filter(OPDVisit.doctor_id == doctor_id)
    return query.order_by(OPDVisit.visit_date.desc()).limit(limit).all()


@router.get("/visits/{visit_id}", response_model=OPDVisitResponse)
async def get_opd_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = db.query(OPDVisit).filter(OPDVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.put("/visits/{visit_id}", response_model=OPDVisitResponse)
async def update_opd_visit(
    visit_id: int, data: OPDVisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = db.query(OPDVisit).filter(OPDVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(visit, field, value)
    if data.weight_kg or data.blood_pressure_systolic:
        visit.bmi = calc_bmi(visit.weight_kg, visit.height_cm)
    db.commit()
    db.refresh(visit)
    return visit


@router.post("/visits/{visit_id}/prescriptions")
async def add_prescription(
    visit_id: int,
    drug_name: str, dosage: str, frequency: str,
    duration_days: int, route: str = "oral",
    instructions: Optional[str] = None, quantity: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = db.query(OPDVisit).filter(OPDVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    prescription = Prescription(
        opd_visit_id=visit_id, drug_name=drug_name,
        dosage=dosage, frequency=frequency,
        duration_days=duration_days, route=route,
        instructions=instructions, quantity=quantity
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/follow-ups")
async def get_follow_ups(
    doctor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import date
    query = db.query(OPDVisit).filter(
        OPDVisit.follow_up_required == True,
        OPDVisit.follow_up_date >= date.today()
    )
    if doctor_id:
        query = query.filter(OPDVisit.doctor_id == doctor_id)
    visits = query.order_by(OPDVisit.follow_up_date.asc()).all()
    return [{"visit_id": v.id, "visit_number": v.visit_number,
             "patient_id": v.patient_id, "follow_up_date": v.follow_up_date,
             "follow_up_notes": v.follow_up_notes} for v in visits]


@router.get("/dashboard/stats")
async def opd_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import date
    from sqlalchemy import func, Date
    today = date.today()
    today_visits = db.query(OPDVisit).filter(
        func.cast(OPDVisit.visit_date, Date) == today).count()
    pending = db.query(OPDVisit).filter(OPDVisit.status == "waiting").count()
    follow_ups = db.query(OPDVisit).filter(
        OPDVisit.follow_up_required == True,
        OPDVisit.follow_up_date == today).count()
    total_visits = db.query(OPDVisit).count()
    return {
        "today_visits": today_visits, "pending_consultations": pending,
        "today_follow_ups": follow_ups, "total_visits": total_visits
    }




