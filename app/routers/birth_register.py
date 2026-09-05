from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.birth_register import BirthRegister, BirthBaby
from app.models.patient import Patient
from app.models.user import User
from app.schemas.birth_register import (
    BirthRegisterCreate,
    BirthRegisterResponse,
    CertificateIssueRequest,
    LinkBabyToPatientRequest,
    BabyResponse,
)

router = APIRouter(prefix="/birth-register", tags=["Birth Register"])


@router.post("", response_model=BirthRegisterResponse, status_code=201)
async def register_birth(
    data: BirthRegisterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mother = db.query(Patient).filter(Patient.id == data.mother_patient_id).first()
    if not mother:
        raise HTTPException(status_code=404, detail="Mother patient record not found")
    if not data.babies:
        raise HTTPException(status_code=400, detail="At least one baby record is required")

    babies_data = data.babies
    register_data = data.model_dump(exclude={"babies"})
    register_data["registered_by"] = current_user.id

    attempt_base = next_sequence_number(db, BirthRegister)
    birth_register = None
    last_error = None
    for i in range(MAX_RETRIES):
        register_data["birth_register_number"] = f"BR{attempt_base + i:07d}"
        birth_register = BirthRegister(**register_data)
        db.add(birth_register)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            birth_register = None
    if last_error:
        raise last_error

    for baby_data in babies_data:
        baby = BirthBaby(**baby_data.model_dump(), birth_register_id=birth_register.id)
        db.add(baby)

    db.commit()
    db.refresh(birth_register)
    return birth_register


@router.get("", response_model=list[BirthRegisterResponse])
async def list_birth_registers(
    mother_patient_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(BirthRegister)
    if mother_patient_id:
        q = q.filter(BirthRegister.mother_patient_id == mother_patient_id)
    return q.order_by(BirthRegister.delivery_datetime.desc()).limit(limit).all()


@router.get("/{register_id}", response_model=BirthRegisterResponse)
async def get_birth_register(
    register_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reg = db.query(BirthRegister).filter(BirthRegister.id == register_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Birth register not found")
    return reg


@router.put("/babies/{baby_id}/certificate", response_model=BabyResponse)
async def issue_birth_certificate(
    baby_id: int,
    data: CertificateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    baby = db.query(BirthBaby).filter(BirthBaby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="Baby record not found")
    if baby.certificate_issued:
        raise HTTPException(status_code=400, detail="Certificate already issued for this baby")

    baby.certificate_number = data.certificate_number
    baby.certificate_issued = True
    baby.certificate_issued_date = datetime.utcnow()
    db.commit()
    db.refresh(baby)
    return baby


@router.put("/babies/{baby_id}/link-patient", response_model=BabyResponse)
async def link_baby_to_patient(
    baby_id: int,
    data: LinkBabyToPatientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Once the baby is formally registered as a patient (gets their own
    UHID), link that patient record here."""
    baby = db.query(BirthBaby).filter(BirthBaby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="Baby record not found")
    patient = db.query(Patient).filter(Patient.id == data.baby_patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    baby.baby_patient_id = data.baby_patient_id
    db.commit()
    db.refresh(baby)
    return baby


@router.get("/dashboard/stats")
async def birth_register_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.birth_register import BirthStatus

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    births_today = db.query(BirthRegister).filter(BirthRegister.delivery_datetime >= today_start).count()
    total_babies_today = (
        db.query(BirthBaby)
        .join(BirthRegister, BirthBaby.birth_register_id == BirthRegister.id)
        .filter(BirthRegister.delivery_datetime >= today_start)
        .count()
    )
    live_births_today = (
        db.query(BirthBaby)
        .join(BirthRegister, BirthBaby.birth_register_id == BirthRegister.id)
        .filter(BirthRegister.delivery_datetime >= today_start, BirthBaby.birth_status == BirthStatus.LIVE_BIRTH)
        .count()
    )
    pending_certificates = (
        db.query(BirthBaby)
        .filter(BirthBaby.certificate_issued == False)  # noqa: E712
        .count()
    )

    return {
        "births_today": births_today,
        "total_babies_today": total_babies_today,
        "live_births_today": live_births_today,
        "pending_certificates": pending_certificates,
    }
