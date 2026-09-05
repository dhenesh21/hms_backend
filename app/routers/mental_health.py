from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mental_health import PsychiatricAssessment, MentalHealthCarePlan, TherapySession, MentalHealthPlanStatus
from app.models.user import User
from app.schemas.mental_health import (
    PsychAssessmentCreate, PsychAssessmentResponse,
    MHCarePlanCreate, MHCarePlanResponse,
    TherapySessionCreate, TherapySessionUpdate, TherapySessionResponse,
)

router = APIRouter(prefix="/mental-health", tags=["Mental Health / Psychiatry"])


@router.post("/assessments", response_model=PsychAssessmentResponse, status_code=201)
async def create_assessment(data: PsychAssessmentCreate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    assessment = PsychiatricAssessment(**data.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/assessments/patient/{patient_id}", response_model=List[PsychAssessmentResponse])
async def list_assessments(patient_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(PsychiatricAssessment).filter(
        PsychiatricAssessment.patient_id == patient_id
    ).order_by(PsychiatricAssessment.assessed_at.desc()).all()


@router.get("/high-risk", response_model=List[PsychAssessmentResponse])
async def high_risk_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Worklist of assessments flagging high/imminent risk — for care coordination follow-up."""
    return db.query(PsychiatricAssessment).filter(
        PsychiatricAssessment.risk_self_harm.in_(["high", "imminent"])
    ).order_by(PsychiatricAssessment.assessed_at.desc()).all()


@router.post("/care-plans", response_model=MHCarePlanResponse, status_code=201)
async def create_care_plan(data: MHCarePlanCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    plan = MentalHealthCarePlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/care-plans/patient/{patient_id}", response_model=List[MHCarePlanResponse])
async def list_care_plans(patient_id: int, active_only: bool = True, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    q = db.query(MentalHealthCarePlan).filter(MentalHealthCarePlan.patient_id == patient_id)
    if active_only:
        q = q.filter(MentalHealthCarePlan.status == MentalHealthPlanStatus.ACTIVE)
    return q.all()


@router.post("/therapy-sessions", response_model=TherapySessionResponse, status_code=201)
async def schedule_session(data: TherapySessionCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    session = TherapySession(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/therapy-sessions/plan/{care_plan_id}", response_model=List[TherapySessionResponse])
async def list_sessions(care_plan_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(TherapySession).filter(
        TherapySession.care_plan_id == care_plan_id
    ).order_by(TherapySession.scheduled_at.desc()).all()


@router.patch("/therapy-sessions/{session_id}", response_model=TherapySessionResponse)
async def update_session(session_id: int, data: TherapySessionUpdate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(session, k, v)
    db.commit()
    db.refresh(session)
    return session
