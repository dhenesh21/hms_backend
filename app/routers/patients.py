from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, create_with_retry
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientListResponse, PaginatedPatients

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payload = data.model_dump()

    def build(n: int) -> Patient:
        return Patient(**payload, uhid=f"UHID{n:07d}", registered_by=current_user.id)

    return create_with_retry(db, Patient, build)


@router.get("/", response_model=PaginatedPatients)
async def list_patients(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Patient).filter(Patient.is_active == True)
    if search:
        query = query.filter(or_(
            Patient.first_name.ilike(f"%{search}%"),
            Patient.last_name.ilike(f"%{search}%"),
            Patient.uhid.ilike(f"%{search}%"),
            Patient.phone.ilike(f"%{search}%")
        ))
    total = query.count()
    # patients = query.offset((page - 1) * size).limit(size).all()
    patients = query.order_by(Patient.id).offset((page - 1) * size).limit(size).all()
    return PaginatedPatients(total=total, page=page, size=size, patients=patients)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/uhid/{uhid}", response_model=PatientResponse)
async def get_patient_by_uhid(
    uhid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.uhid == uhid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}")
async def deactivate_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_active = False
    db.commit()
    return {"message": "Patient deactivated"}


@router.get("/{patient_id}/history")
async def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient_id": patient_id,
        "opd_visits": len(patient.opd_visits),
        "admissions": len(patient.admissions),
        "appointments": len(patient.appointments),
        "visits": [{"id": v.id, "visit_number": v.visit_number, "visit_date": v.visit_date,
                    "primary_diagnosis": v.primary_diagnosis, "status": v.status}
                   for v in patient.opd_visits],
        "admissions_list": [{"id": a.id, "admission_number": a.admission_number,
                             "admission_date": a.admission_date, "status": a.status}
                            for a in patient.admissions]
    }


