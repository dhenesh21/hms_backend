from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dialysis import DialysisPatientProfile, DialysisSession, DialysisSessionStatus
from app.models.user import User
from app.schemas.dialysis import (
    DialysisProfileCreate, DialysisProfileResponse,
    DialysisSessionCreate, DialysisSessionUpdate, DialysisSessionResponse,
)

router = APIRouter(prefix="/dialysis", tags=["Dialysis"])


@router.post("/profiles", response_model=DialysisProfileResponse, status_code=201)
async def create_profile(data: DialysisProfileCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    existing = db.query(DialysisPatientProfile).filter(DialysisPatientProfile.patient_id == data.patient_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dialysis profile already exists for this patient")
    profile = DialysisPatientProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles", response_model=List[DialysisProfileResponse])
async def list_profiles(active_only: bool = True, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(DialysisPatientProfile)
    if active_only:
        q = q.filter(DialysisPatientProfile.is_active == True)
    return q.all()


@router.get("/profiles/patient/{patient_id}", response_model=DialysisProfileResponse)
async def get_profile(patient_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    profile = db.query(DialysisPatientProfile).filter(DialysisPatientProfile.patient_id == patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No dialysis profile for this patient")
    return profile


@router.post("/sessions", response_model=DialysisSessionResponse, status_code=201)
async def schedule_session(data: DialysisSessionCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    session = DialysisSession(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/profile/{profile_id}", response_model=List[DialysisSessionResponse])
async def list_sessions(profile_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(DialysisSession).filter(
        DialysisSession.profile_id == profile_id
    ).order_by(DialysisSession.scheduled_at.desc()).all()


@router.get("/sessions/today", response_model=List[DialysisSessionResponse])
async def sessions_today(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    return db.query(DialysisSession).filter(
        DialysisSession.status.in_([DialysisSessionStatus.SCHEDULED, DialysisSessionStatus.IN_PROGRESS])
    ).all()


@router.patch("/sessions/{session_id}", response_model=DialysisSessionResponse)
async def update_session(session_id: int, data: DialysisSessionUpdate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    session = db.query(DialysisSession).filter(DialysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(session, k, v)
    if data.status == DialysisSessionStatus.IN_PROGRESS and not session.started_at:
        session.started_at = datetime.now(timezone.utc)
    if data.status == DialysisSessionStatus.COMPLETED and not session.completed_at:
        session.completed_at = datetime.now(timezone.utc)
        if session.started_at:
            session.duration_minutes = int((session.completed_at - session.started_at).total_seconds() // 60)
    db.commit()
    db.refresh(session)
    return session
