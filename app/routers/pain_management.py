from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.pain_management import PainManagementPlan, PainAssessment
from app.models.user import User
from app.schemas.pain_management import (
    PainPlanCreate, PainPlanResponse,
    PainAssessmentCreate, PainAssessmentResponse,
)

router = APIRouter(prefix="/pain-management", tags=["Pain Management"])


@router.post("/plans", response_model=PainPlanResponse, status_code=201)
async def create_plan(data: PainPlanCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    plan = PainManagementPlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=List[PainPlanResponse])
async def list_plans(patient_id: Optional[int] = None, active_only: bool = True,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(PainManagementPlan)
    if patient_id:
        q = q.filter(PainManagementPlan.patient_id == patient_id)
    if active_only:
        q = q.filter(PainManagementPlan.is_active == True)
    return q.order_by(PainManagementPlan.created_at.desc()).all()


@router.post("/plans/{plan_id}/close", response_model=PainPlanResponse)
async def close_plan(plan_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    plan = db.query(PainManagementPlan).filter(PainManagementPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    plan.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/assessments", response_model=PainAssessmentResponse, status_code=201)
async def add_assessment(data: PainAssessmentCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    assessment = PainAssessment(**data.model_dump(), assessed_by=current_user.id)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/assessments/plan/{plan_id}", response_model=List[PainAssessmentResponse])
async def list_assessments(plan_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(PainAssessment).filter(
        PainAssessment.plan_id == plan_id
    ).order_by(PainAssessment.assessed_at.desc()).all()
