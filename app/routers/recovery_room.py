from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recovery_room import RecoveryRoomStay, RecoveryRoomObservation, RecoveryStatus
from app.models.user import User
from app.schemas.recovery_room import (
    RecoveryStayCreate, RecoveryStayDischarge, RecoveryStayResponse,
    RecoveryObservationCreate, RecoveryObservationResponse,
)

router = APIRouter(prefix="/recovery-room", tags=["Recovery Room / PACU"])


@router.post("/stays", response_model=RecoveryStayResponse, status_code=201)
async def admit_to_recovery(data: RecoveryStayCreate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    existing = db.query(RecoveryRoomStay).filter(RecoveryRoomStay.surgery_id == data.surgery_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Recovery stay already exists for this surgery")
    stay = RecoveryRoomStay(**data.model_dump(), admitted_by=current_user.id)
    db.add(stay)
    db.commit()
    db.refresh(stay)
    return stay


@router.get("/stays", response_model=List[RecoveryStayResponse])
async def list_active_stays(status: Optional[RecoveryStatus] = None, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    q = db.query(RecoveryRoomStay)
    if status:
        q = q.filter(RecoveryRoomStay.status == status)
    else:
        q = q.filter(RecoveryRoomStay.status == RecoveryStatus.IN_RECOVERY)
    return q.order_by(RecoveryRoomStay.admitted_at).all()


@router.get("/stays/surgery/{surgery_id}", response_model=RecoveryStayResponse)
async def get_stay_for_surgery(surgery_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    stay = db.query(RecoveryRoomStay).filter(RecoveryRoomStay.surgery_id == surgery_id).first()
    if not stay:
        raise HTTPException(status_code=404, detail="No recovery stay for this surgery")
    return stay


@router.post("/stays/{stay_id}/observations", response_model=RecoveryObservationResponse, status_code=201)
async def add_observation(stay_id: int, data: RecoveryObservationCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    obs = RecoveryRoomObservation(**data.model_dump(), recorded_by=current_user.id)
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.get("/stays/{stay_id}/observations", response_model=List[RecoveryObservationResponse])
async def list_observations(stay_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return db.query(RecoveryRoomObservation).filter(
        RecoveryRoomObservation.recovery_stay_id == stay_id
    ).order_by(RecoveryRoomObservation.recorded_at).all()


@router.post("/stays/{stay_id}/discharge", response_model=RecoveryStayResponse)
async def discharge_from_recovery(stay_id: int, data: RecoveryStayDischarge, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    stay = db.query(RecoveryRoomStay).filter(RecoveryRoomStay.id == stay_id).first()
    if not stay:
        raise HTTPException(status_code=404, detail="Recovery stay not found")
    if stay.status != RecoveryStatus.IN_RECOVERY:
        raise HTTPException(status_code=400, detail="Patient is not currently in recovery")

    stay.discharge_destination = data.discharge_destination
    stay.discharge_notes = data.discharge_notes
    if data.aldrete_score is not None:
        stay.aldrete_score = data.aldrete_score
    stay.status = (RecoveryStatus.DISCHARGED_TO_ICU if data.discharge_destination.lower() == "icu"
                   else RecoveryStatus.DISCHARGED_TO_WARD)
    stay.discharged_at = datetime.now(timezone.utc)
    stay.discharged_by = current_user.id
    db.commit()
    db.refresh(stay)
    return stay
