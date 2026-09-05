from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.physiotherapy import PhysiotherapyPlan, PhysiotherapySession, RehabPlanStatus, SessionStatus
from app.models.user import User
from app.schemas.physiotherapy import (
    PhysioPlanCreate, PhysioPlanResponse,
    PhysioSessionCreate, PhysioSessionComplete, PhysioSessionResponse,
)

router = APIRouter(prefix="/physiotherapy", tags=["Physiotherapy / Rehabilitation"])


@router.post("/plans", response_model=PhysioPlanResponse, status_code=201)
async def create_plan(data: PhysioPlanCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    plan = PhysiotherapyPlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=List[PhysioPlanResponse])
async def list_plans(patient_id: Optional[int] = None, status: Optional[RehabPlanStatus] = None,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(PhysiotherapyPlan)
    if patient_id:
        q = q.filter(PhysiotherapyPlan.patient_id == patient_id)
    if status:
        q = q.filter(PhysiotherapyPlan.status == status)
    return q.order_by(PhysiotherapyPlan.started_on.desc()).all()


@router.post("/plans/{plan_id}/complete", response_model=PhysioPlanResponse)
async def complete_plan(plan_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    plan = db.query(PhysiotherapyPlan).filter(PhysiotherapyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = RehabPlanStatus.COMPLETED
    from datetime import date
    plan.ended_on = date.today()
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/sessions", response_model=PhysioSessionResponse, status_code=201)
async def schedule_session(data: PhysioSessionCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    session = PhysiotherapySession(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/plan/{plan_id}", response_model=List[PhysioSessionResponse])
async def list_sessions(plan_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(PhysiotherapySession).filter(
        PhysiotherapySession.plan_id == plan_id
    ).order_by(PhysiotherapySession.scheduled_at).all()


@router.post("/sessions/{session_id}/complete", response_model=PhysioSessionResponse)
async def complete_session(session_id: int, data: PhysioSessionComplete, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    session = db.query(PhysiotherapySession).filter(PhysiotherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    for k, v in data.model_dump().items():
        setattr(session, k, v)
    session.status = SessionStatus.COMPLETED
    session.therapist_id = session.therapist_id or current_user.id
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/mark-missed", response_model=PhysioSessionResponse)
async def mark_missed(session_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    session = db.query(PhysiotherapySession).filter(PhysiotherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.MISSED
    db.commit()
    db.refresh(session)
    return session
