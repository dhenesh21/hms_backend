from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.palliative_care import PalliativeCarePlan, SymptomAssessment
from app.models.user import User
from app.schemas.palliative_care import (
    PalliativePlanCreate, PalliativePlanClose, PalliativePlanResponse,
    SymptomAssessmentCreate, SymptomAssessmentResponse,
)

router = APIRouter(prefix="/palliative-care", tags=["Palliative / Hospice Care"])


@router.post("/plans", response_model=PalliativePlanResponse, status_code=201)
async def create_plan(data: PalliativePlanCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    plan = PalliativeCarePlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=List[PalliativePlanResponse])
async def list_plans(patient_id: Optional[int] = None, active_only: bool = True,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(PalliativeCarePlan)
    if patient_id:
        q = q.filter(PalliativeCarePlan.patient_id == patient_id)
    if active_only:
        q = q.filter(PalliativeCarePlan.is_active == True)
    return q.order_by(PalliativeCarePlan.started_at.desc()).all()


@router.post("/plans/{plan_id}/close", response_model=PalliativePlanResponse)
async def close_plan(plan_id: int, data: PalliativePlanClose, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    plan = db.query(PalliativeCarePlan).filter(PalliativeCarePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    plan.closed_at = datetime.now(timezone.utc)
    plan.closure_reason = data.closure_reason
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/symptom-assessments", response_model=SymptomAssessmentResponse, status_code=201)
async def add_symptom_assessment(data: SymptomAssessmentCreate, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    assessment = SymptomAssessment(**data.model_dump(), assessed_by=current_user.id)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/symptom-assessments/plan/{plan_id}", response_model=List[SymptomAssessmentResponse])
async def list_symptom_assessments(plan_id: int, db: Session = Depends(get_db),
                                    current_user: User = Depends(get_current_user)):
    return db.query(SymptomAssessment).filter(
        SymptomAssessment.care_plan_id == plan_id
    ).order_by(SymptomAssessment.assessed_at.desc()).all()
