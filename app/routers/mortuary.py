from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.mortuary import MortuaryRecord, BodyStatus
from app.models.patient import Patient
from app.models.user import User
from app.schemas.mortuary import (
    MortuaryRecordCreate,
    MortuaryRecordUpdate,
    MortuaryRecordResponse,
    PostmortemUpdate,
    ReleaseRequest,
    CertificateIssueRequest,
)

router = APIRouter(prefix="/mortuary", tags=["Mortuary"])


@router.post("/records", response_model=MortuaryRecordResponse, status_code=201)
async def register_death(
    data: MortuaryRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing = (
        db.query(MortuaryRecord)
        .filter(MortuaryRecord.patient_id == data.patient_id, MortuaryRecord.body_status != BodyStatus.RELEASED)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="An active mortuary record already exists for this patient")

    record_data = data.model_dump()
    record_data["registered_by"] = current_user.id

    attempt_base = next_sequence_number(db, MortuaryRecord)
    record = None
    last_error = None
    for i in range(MAX_RETRIES):
        record_data["mortuary_number"] = f"MOR{attempt_base + i:06d}"
        record = MortuaryRecord(**record_data)
        db.add(record)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            record = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(record)
    return record


@router.get("/records", response_model=list[MortuaryRecordResponse])
async def list_records(
    body_status: Optional[BodyStatus] = Query(None),
    is_mlc: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(MortuaryRecord)
    if body_status:
        q = q.filter(MortuaryRecord.body_status == body_status)
    if is_mlc is not None:
        q = q.filter(MortuaryRecord.is_mlc == is_mlc)
    return q.order_by(MortuaryRecord.date_of_death.desc()).limit(limit).all()


@router.get("/records/in-storage", response_model=list[MortuaryRecordResponse])
async def bodies_in_storage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(MortuaryRecord)
        .filter(MortuaryRecord.body_status.in_([BodyStatus.IN_STORAGE, BodyStatus.IN_POSTMORTEM]))
        .order_by(MortuaryRecord.stored_at.asc())
        .all()
    )


@router.get("/records/{record_id}", response_model=MortuaryRecordResponse)
async def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    return record


@router.put("/records/{record_id}", response_model=MortuaryRecordResponse)
async def update_record(
    record_id: int,
    data: MortuaryRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    if record.body_status == BodyStatus.RELEASED:
        raise HTTPException(status_code=400, detail="Cannot update a released record")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.put("/records/{record_id}/postmortem/start", response_model=MortuaryRecordResponse)
async def start_postmortem(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    if not record.postmortem_required:
        raise HTTPException(status_code=400, detail="Postmortem was not marked as required for this record")
    if record.body_status != BodyStatus.IN_STORAGE:
        raise HTTPException(status_code=400, detail=f"Cannot start postmortem from status '{record.body_status.value}'")

    record.body_status = BodyStatus.IN_POSTMORTEM
    db.commit()
    db.refresh(record)
    return record


@router.put("/records/{record_id}/postmortem/complete", response_model=MortuaryRecordResponse)
async def complete_postmortem(
    record_id: int,
    data: PostmortemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    if record.body_status != BodyStatus.IN_POSTMORTEM:
        raise HTTPException(status_code=400, detail="Postmortem has not been started for this record")

    record.postmortem_done = True
    record.postmortem_date = datetime.utcnow()
    record.postmortem_doctor = data.postmortem_doctor
    record.postmortem_findings = data.postmortem_findings
    record.body_status = BodyStatus.IN_STORAGE  # back to storage pending release
    db.commit()
    db.refresh(record)
    return record


@router.put("/records/{record_id}/release", response_model=MortuaryRecordResponse)
async def release_body(
    record_id: int,
    data: ReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    if record.body_status == BodyStatus.RELEASED:
        raise HTTPException(status_code=400, detail="Body has already been released")
    if record.postmortem_required and not record.postmortem_done:
        raise HTTPException(status_code=400, detail="Cannot release: required postmortem has not been completed")

    record.body_status = BodyStatus.RELEASED
    record.released_to = data.released_to
    record.released_relation = data.released_relation
    record.release_date = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.put("/records/{record_id}/certificate", response_model=MortuaryRecordResponse)
async def issue_death_certificate(
    record_id: int,
    data: CertificateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MortuaryRecord).filter(MortuaryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mortuary record not found")
    if record.death_certificate_issued:
        raise HTTPException(status_code=400, detail="Death certificate already issued")

    record.death_certificate_number = data.death_certificate_number
    record.death_certificate_issued = True
    db.commit()
    db.refresh(record)
    return record


@router.get("/dashboard/stats")
async def mortuary_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    in_storage = db.query(MortuaryRecord).filter(MortuaryRecord.body_status == BodyStatus.IN_STORAGE).count()
    in_postmortem = db.query(MortuaryRecord).filter(MortuaryRecord.body_status == BodyStatus.IN_POSTMORTEM).count()
    deaths_today = db.query(MortuaryRecord).filter(MortuaryRecord.date_of_death >= today_start).count()
    pending_certificates = (
        db.query(MortuaryRecord)
        .filter(MortuaryRecord.death_certificate_issued == False)  # noqa: E712
        .count()
    )
    mlc_pending_postmortem = (
        db.query(MortuaryRecord)
        .filter(MortuaryRecord.is_mlc == True, MortuaryRecord.postmortem_required == True, MortuaryRecord.postmortem_done == False)  # noqa: E712
        .count()
    )

    return {
        "in_storage": in_storage,
        "in_postmortem": in_postmortem,
        "deaths_today": deaths_today,
        "pending_certificates": pending_certificates,
        "mlc_pending_postmortem": mlc_pending_postmortem,
    }
