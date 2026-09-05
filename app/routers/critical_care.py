from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.critical_care import CriticalCareAdmission, CriticalCareRound, CriticalCareUnit
from app.models.ipd import IPDAdmission
from app.models.user import User
from app.schemas.critical_care import (
    CriticalCareAdmissionCreate,
    CriticalCareAdmissionUpdate,
    CriticalCareAdmissionResponse,
    CriticalCareAdmissionDetailResponse,
    StepDownRequest,
    RoundCreate,
    RoundResponse,
)

router = APIRouter(prefix="/critical-care", tags=["Critical Care (ICU/CCU/NICU)"])


@router.post("/admissions", response_model=CriticalCareAdmissionDetailResponse, status_code=201)
async def admit_to_critical_care(
    data: CriticalCareAdmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ipd_admission = db.query(IPDAdmission).filter(IPDAdmission.id == data.ipd_admission_id).first()
    if not ipd_admission:
        raise HTTPException(status_code=404, detail="IPD admission not found")

    existing = (
        db.query(CriticalCareAdmission)
        .filter(
            CriticalCareAdmission.ipd_admission_id == data.ipd_admission_id,
            CriticalCareAdmission.is_active == True,  # noqa: E712
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This IPD admission already has an active critical care record",
        )

    admission = CriticalCareAdmission(**data.model_dump(), admitted_by=current_user.id)
    db.add(admission)
    db.commit()
    db.refresh(admission)
    return admission


@router.get("/admissions", response_model=list[CriticalCareAdmissionResponse])
async def list_critical_care_admissions(
    unit_type: Optional[CriticalCareUnit] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CriticalCareAdmission)
    if unit_type:
        q = q.filter(CriticalCareAdmission.unit_type == unit_type)
    if active_only:
        q = q.filter(CriticalCareAdmission.is_active == True)  # noqa: E712
    return q.order_by(CriticalCareAdmission.admitted_at.desc()).all()


@router.get("/admissions/{admission_id}", response_model=CriticalCareAdmissionDetailResponse)
async def get_critical_care_admission(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    admission = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Critical care admission not found")
    return admission


@router.put("/admissions/{admission_id}", response_model=CriticalCareAdmissionResponse)
async def update_critical_care_admission(
    admission_id: int,
    data: CriticalCareAdmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    admission = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Critical care admission not found")
    if not admission.is_active:
        raise HTTPException(status_code=400, detail="Cannot update a stepped-down critical care record")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(admission, field, value)

    db.commit()
    db.refresh(admission)
    return admission


@router.post("/admissions/{admission_id}/step-down", response_model=CriticalCareAdmissionResponse)
async def step_down(
    admission_id: int,
    data: StepDownRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark the patient as stepped down from critical care (moved to a general ward)."""
    admission = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Critical care admission not found")
    if not admission.is_active:
        raise HTTPException(status_code=400, detail="Already stepped down")

    admission.is_active = False
    admission.stepped_down_at = datetime.utcnow()
    admission.step_down_notes = data.step_down_notes
    db.commit()
    db.refresh(admission)
    return admission


@router.post("/admissions/{admission_id}/rounds", response_model=RoundResponse, status_code=201)
async def add_round(
    admission_id: int,
    data: RoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    admission = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Critical care admission not found")
    if not admission.is_active:
        raise HTTPException(status_code=400, detail="Cannot add rounds to a stepped-down record")

    round_entry = CriticalCareRound(
        **data.model_dump(), critical_care_admission_id=admission_id, recorded_by=current_user.id
    )
    db.add(round_entry)
    db.commit()
    db.refresh(round_entry)
    return round_entry


@router.get("/admissions/{admission_id}/rounds", response_model=list[RoundResponse])
async def list_rounds(
    admission_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    admission = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Critical care admission not found")
    return (
        db.query(CriticalCareRound)
        .filter(CriticalCareRound.critical_care_admission_id == admission_id)
        .order_by(CriticalCareRound.recorded_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/dashboard/stats")
async def critical_care_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_q = db.query(CriticalCareAdmission).filter(CriticalCareAdmission.is_active == True)  # noqa: E712

    total_active = active_q.count()
    by_unit = {
        unit.value: active_q.filter(CriticalCareAdmission.unit_type == unit).count()
        for unit in CriticalCareUnit
    }
    on_ventilator = active_q.filter(CriticalCareAdmission.on_ventilator == True).count()  # noqa: E712

    return {
        "total_active": total_active,
        "by_unit": by_unit,
        "on_ventilator": on_ventilator,
    }
