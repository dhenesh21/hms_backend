from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.doctor import DoctorProfile, DutyRoster
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User, UserRole
from app.schemas.doctor import (
    DoctorProfileCreate, DoctorProfileResponse,
    DutyRosterCreate, DutyRosterResponse,
    AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentDetailResponse
)

router = APIRouter(tags=["Doctors & Appointments"])


# ── DOCTOR ROUTES ──────────────────────────────────────
@router.post("/doctors/profile", response_model=DoctorProfileResponse, status_code=201)
async def create_doctor_profile(
    data: DoctorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    existing = db.query(DoctorProfile).filter(DoctorProfile.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Doctor profile already exists")
    profile = DoctorProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/doctors/{doctor_id}/profile")
async def update_doctor_profile(
    doctor_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update doctor fee, availability, consultation duration, bio"""
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    allowed = {"consultation_fee", "consultation_duration_minutes", "is_available",
               "bio", "available_days", "languages_spoken", "experience_years",
               "specialization", "sub_specialization", "qualification"}
    for key, val in data.items():
        if key in allowed:
            setattr(doctor, key, val)
    db.commit()
    db.refresh(doctor)
    return {"message": "Doctor profile updated", "id": doctor_id}


@router.get("/doctors")
async def list_doctors(
    specialization: Optional[str] = Query(None),
    available_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(DoctorProfile).join(User)
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    if available_only:
        query = query.filter(DoctorProfile.is_available == True)
    doctors = query.all()
    result = []
    for d in doctors:
        result.append({
            "id": d.id, "user_id": d.user_id,
            "full_name": d.user.full_name, "email": d.user.email,
            "specialization": d.specialization, "sub_specialization": d.sub_specialization,
            "qualification": d.qualification, "experience_years": d.experience_years,
            "consultation_fee": d.consultation_fee, "is_available": d.is_available,
            "available_days": d.available_days
        })
    return result


@router.get("/doctors/{doctor_id}")
async def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(DoctorProfile).options(joinedload(DoctorProfile.user)).filter(
        DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {
        "id": doctor.id, "user_id": doctor.user_id,
        "full_name": doctor.user.full_name, "email": doctor.user.email,
        "specialization": doctor.specialization, "qualification": doctor.qualification,
        "experience_years": doctor.experience_years, "consultation_fee": doctor.consultation_fee,
        "bio": doctor.bio, "languages_spoken": doctor.languages_spoken,
        "available_days": doctor.available_days,
        "consultation_duration_minutes": doctor.consultation_duration_minutes,
        "is_available": doctor.is_available,
        "roster": [{"day": r.day_of_week, "start": r.start_time, "end": r.end_time}
                   for r in doctor.duty_roster if r.is_active]
    }


@router.post("/doctors/{doctor_id}/roster", response_model=DutyRosterResponse, status_code=201)
async def add_duty_roster(
    doctor_id: int, data: DutyRosterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    roster = DutyRoster(**data.model_dump(), doctor_id=doctor_id)
    db.add(roster)
    db.commit()
    db.refresh(roster)
    return roster


@router.get("/doctors/{doctor_id}/available-slots")
async def get_available_slots(
    doctor_id: int, appointment_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    day_name = appointment_date.strftime("%A")
    roster = db.query(DutyRoster).filter(
        DutyRoster.doctor_id == doctor_id,
        DutyRoster.day_of_week == day_name,
        DutyRoster.is_active == True
    ).first()

    if not roster:
        return {"slots": [], "message": f"Doctor not available on {day_name}"}

    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status.notin_([AppointmentStatus.CANCELLED])
    ).all()
    booked_times = {a.appointment_time for a in booked}

    # Generate slots
    from datetime import datetime, timedelta
    start = datetime.strptime(roster.start_time, "%H:%M")
    end = datetime.strptime(roster.end_time, "%H:%M")
    slots = []
    current = start
    while current < end:
        time_str = current.strftime("%H:%M")
        slots.append({"time": time_str, "available": time_str not in booked_times})
        current += timedelta(minutes=doctor.consultation_duration_minutes)

    return {"slots": slots, "date": appointment_date, "doctor_id": doctor_id}




@router.get("/doctors/{doctor_id}/roster", response_model=list[DutyRosterResponse])
async def get_doctor_roster(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Doctor-ன் current duty roster பாக்க"""
    return db.query(DutyRoster).filter(DutyRoster.doctor_id == doctor_id).all()


@router.post("/doctors/{doctor_id}/roster/bulk", status_code=201)
async def set_bulk_roster(
    doctor_id: int,
    days: list[DutyRosterCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """ஒரே call-ல multiple days roster set பண்ண — existing roster replace ஆகும்"""
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

   
    db.query(DutyRoster).filter(DutyRoster.doctor_id == doctor_id).delete()

   
    created = []
    for day_data in days:
        roster = DutyRoster(
            doctor_id=doctor_id,
            day_of_week=day_data.day_of_week,
            start_time=day_data.start_time,
            end_time=day_data.end_time,
            max_patients=day_data.max_patients,
            is_active=True
        )
        db.add(roster)
        created.append(roster)

    db.commit()
    return {"message": f"{len(created)} roster entries created", "doctor_id": doctor_id}


@router.delete("/doctors/{doctor_id}/roster/{roster_id}")
async def delete_roster(
    doctor_id: int,
    roster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """Single roster entry delete பண்ண"""
    roster = db.query(DutyRoster).filter(
        DutyRoster.id == roster_id,
        DutyRoster.doctor_id == doctor_id
    ).first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    db.delete(roster)
    db.commit()
    return {"message": "Roster deleted"}


@router.put("/doctors/{doctor_id}/roster/{roster_id}", response_model=DutyRosterResponse)
async def update_roster(
    doctor_id: int,
    roster_id: int,
    data: DutyRosterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """Roster entry update பண்ண"""
    roster = db.query(DutyRoster).filter(
        DutyRoster.id == roster_id,
        DutyRoster.doctor_id == doctor_id
    ).first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    roster.day_of_week = data.day_of_week
    roster.start_time = data.start_time
    roster.end_time = data.end_time
    roster.max_patients = data.max_patients
    db.commit()
    db.refresh(roster)
    return roster

# ── APPOINTMENT ROUTES ─────────────────────────────────
@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check slot availability
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == data.doctor_id,
        Appointment.appointment_date == data.appointment_date,
        Appointment.appointment_time == data.appointment_time,
        Appointment.status.notin_([AppointmentStatus.CANCELLED])
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="This slot is already booked")

    from sqlalchemy.exc import IntegrityError

    appt_number_base = next_sequence_number(db, Appointment)
    appt_data = data.model_dump()
    appt_data["booked_by"] = current_user.id

    appt = None
    last_error = None
    for i in range(MAX_RETRIES):
        # Recompute token count fresh on every attempt - if a concurrent
        # booking landed between our attempts, this picks up the new count.
        token_count = db.query(Appointment).filter(
            Appointment.doctor_id == data.doctor_id,
            Appointment.appointment_date == data.appointment_date,
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).count()

        appt_data["appointment_number"] = f"APT{appt_number_base + i:07d}"
        appt_data["token_number"] = token_count + 1
        appt = Appointment(**appt_data)
        db.add(appt)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            appt = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(appt)
    return appt


@router.get("/appointments")
async def list_appointments(
    doctor_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    appointment_date: Optional[date] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Appointment)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    if appointment_date:
        query = query.filter(Appointment.appointment_date == appointment_date)
    if status:
        query = query.filter(Appointment.status == status)

    appointments = query.order_by(Appointment.appointment_date.desc()).limit(100).all()
    result = []
    for a in appointments:
        result.append({
            "id": a.id, "appointment_number": a.appointment_number,
            "patient_name": f"{a.patient.first_name} {a.patient.last_name}",
            "patient_uhid": a.patient.uhid,
            "doctor_name": a.doctor.user.full_name,
            "specialization": a.doctor.specialization,
            "appointment_date": a.appointment_date, "appointment_time": a.appointment_time,
            "appointment_type": a.appointment_type, "status": a.status,
            "token_number": a.token_number
        })
    return result


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int, data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(appt, field, value)
    db.commit()
    db.refresh(appt)
    return appt





from app.models.patient import Patient as PatientModel

@router.get("/appointments/queue/today")
async def get_today_queue(
    doctor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    query = db.query(Appointment).filter(Appointment.appointment_date == today)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    appts = query.order_by(Appointment.token_number.asc()).all()
    result = []
    for a in appts:
        patient = db.query(PatientModel).filter(PatientModel.id == a.patient_id).first()
        dp = db.query(DoctorProfile).filter(DoctorProfile.id == a.doctor_id).first()
        du = db.query(User).filter(User.id == dp.user_id).first() if dp else None
        result.append({
            "id": a.id, "token_number": a.token_number,
            "appointment_time": str(a.appointment_time),
            "appointment_type": str(a.appointment_type),
            "status": str(a.status), "reason": a.reason,
            "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "—",
            "patient_uhid": patient.uhid if patient else "—",
            "patient_phone": patient.phone if patient else "—",
            "doctor_name": du.full_name if du else "—",
            "doctor_specialization": dp.specialization if dp else "—",
        })
    return {"date": str(today), "total": len(result), "queue": result}


@router.put("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int, data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = data.get("status", appt.status)
    db.commit()
    return {"message": "Status updated", "id": appointment_id}
