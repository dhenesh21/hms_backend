from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.anesthesia import PreAnesthesiaAssessment, AnesthesiaRecord, AnesthesiaVital
from app.models.user import User
from app.schemas.anesthesia import (
    PreAnesthesiaCreate, PreAnesthesiaResponse,
    AnesthesiaRecordCreate, AnesthesiaRecordUpdate, AnesthesiaRecordResponse,
    AnesthesiaVitalCreate, AnesthesiaVitalResponse,
)

router = APIRouter(prefix="/anesthesia", tags=["Anesthesia"])


# ── PRE-ANESTHESIA ASSESSMENT (PAC) ────────────────────
@router.post("/pre-assessments", response_model=PreAnesthesiaResponse, status_code=201)
async def create_pre_assessment(data: PreAnesthesiaCreate, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    assessment = PreAnesthesiaAssessment(**data.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/pre-assessments/surgery/{surgery_id}", response_model=List[PreAnesthesiaResponse])
async def get_pre_assessments_for_surgery(surgery_id: int, db: Session = Depends(get_db),
                                           current_user: User = Depends(get_current_user)):
    return db.query(PreAnesthesiaAssessment).filter(
        PreAnesthesiaAssessment.surgery_id == surgery_id
    ).order_by(PreAnesthesiaAssessment.assessed_at.desc()).all()


# ── INTRA-OP ANESTHESIA RECORD ─────────────────────────
@router.post("/records", response_model=AnesthesiaRecordResponse, status_code=201)
async def start_anesthesia_record(data: AnesthesiaRecordCreate, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    existing = db.query(AnesthesiaRecord).filter(AnesthesiaRecord.surgery_id == data.surgery_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Anesthesia record already exists for this surgery")
    record = AnesthesiaRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/records/surgery/{surgery_id}", response_model=AnesthesiaRecordResponse)
async def get_record_for_surgery(surgery_id: int, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    record = db.query(AnesthesiaRecord).filter(AnesthesiaRecord.surgery_id == surgery_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="No anesthesia record for this surgery")
    return record


@router.patch("/records/{record_id}", response_model=AnesthesiaRecordResponse)
async def update_record(record_id: int, data: AnesthesiaRecordUpdate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    record = db.query(AnesthesiaRecord).filter(AnesthesiaRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Anesthesia record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    return record


# ── INTRA-OP VITALS TREND ──────────────────────────────
@router.post("/records/{record_id}/vitals", response_model=AnesthesiaVitalResponse, status_code=201)
async def add_vital(record_id: int, data: AnesthesiaVitalCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    vital = AnesthesiaVital(**data.model_dump())
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return vital


@router.get("/records/{record_id}/vitals", response_model=List[AnesthesiaVitalResponse])
async def list_vitals(record_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return db.query(AnesthesiaVital).filter(
        AnesthesiaVital.anesthesia_record_id == record_id
    ).order_by(AnesthesiaVital.recorded_at).all()
