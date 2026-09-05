from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.medical_record_privacy import MedicalRecordAccessLog, PatientPrivacyFlag
from app.models.user import User
from app.schemas.medical_record_privacy import (
    LogAccessRequest, AccessLogResponse, PrivacyFlagCreate, PrivacyFlagResponse,
)

router = APIRouter(prefix="/medical-record-privacy", tags=["Medical Record Access Audit / Privacy"])


@router.post("/log-access", response_model=AccessLogResponse, status_code=201)
async def log_access(data: LogAccessRequest, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    """
    Item 291 — call this whenever a clinical record is actually viewed.
    Automatically checks for an active PatientPrivacyFlag and records
    whether this access touched a flagged/restricted record.
    """
    flag = db.query(PatientPrivacyFlag).filter(
        PatientPrivacyFlag.patient_id == data.patient_id, PatientPrivacyFlag.is_active == True).first()

    log = MedicalRecordAccessLog(**data.model_dump(), accessed_by=current_user.id,
                                  was_restricted_record=bool(flag))
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/access-logs/patient/{patient_id}", response_model=List[AccessLogResponse])
async def get_access_logs(patient_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None,
                           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Who has viewed this patient's record, and when — what a patient or a
    regulator asking 'who accessed my records' would need answered."""
    from sqlalchemy import func, Date
    q = db.query(MedicalRecordAccessLog).filter(MedicalRecordAccessLog.patient_id == patient_id)
    if start_date:
        q = q.filter(func.cast(MedicalRecordAccessLog.created_at, Date) >= start_date)
    if end_date:
        q = q.filter(func.cast(MedicalRecordAccessLog.created_at, Date) <= end_date)
    return q.order_by(MedicalRecordAccessLog.created_at.desc()).limit(500).all()


@router.get("/access-logs/user/{user_id}", response_model=List[AccessLogResponse])
async def get_access_logs_by_user(user_id: int, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    """The reverse view — everything a specific staff member has accessed,
    for investigating a suspected inappropriate-access complaint."""
    return db.query(MedicalRecordAccessLog).filter(
        MedicalRecordAccessLog.accessed_by == user_id
    ).order_by(MedicalRecordAccessLog.created_at.desc()).limit(500).all()


# ── PRIVACY FLAGS (item 289) ────────────────────────────
@router.post("/privacy-flags", response_model=PrivacyFlagResponse, status_code=201)
async def flag_patient_privacy(data: PrivacyFlagCreate, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    existing = db.query(PatientPrivacyFlag).filter(
        PatientPrivacyFlag.patient_id == data.patient_id, PatientPrivacyFlag.is_active == True).first()
    if existing:
        raise HTTPException(status_code=400, detail="This patient already has an active privacy flag")

    flag = PatientPrivacyFlag(**data.model_dump(), flagged_by=current_user.id)
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


@router.get("/privacy-flags/patient/{patient_id}", response_model=Optional[PrivacyFlagResponse])
async def get_privacy_flag(patient_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(PatientPrivacyFlag).filter(
        PatientPrivacyFlag.patient_id == patient_id, PatientPrivacyFlag.is_active == True).first()


@router.delete("/privacy-flags/{flag_id}", status_code=204)
async def remove_privacy_flag(flag_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    flag = db.query(PatientPrivacyFlag).filter(PatientPrivacyFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Privacy flag not found")
    flag.is_active = False
    db.commit()
