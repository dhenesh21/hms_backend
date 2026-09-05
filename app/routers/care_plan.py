from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.care_plan import (ClinicalPathwayTemplate, PatientCarePlan, CarePlanTask,
                                   PathwayStatus, TaskStatus)
from app.models.user import User
from app.schemas.care_plan import (
    PathwayTemplateCreate, PathwayTemplateResponse,
    CarePlanCreateFromTemplate, CarePlanCreateCustom, CarePlanResponse,
    CarePlanTaskResponse, CarePlanTaskUpdate,
)

router = APIRouter(prefix="/care-plans", tags=["Clinical Pathways / Care Plans"])


# ── PATHWAY TEMPLATES ──────────────────────────────────
@router.post("/templates", response_model=PathwayTemplateResponse, status_code=201)
async def create_pathway_template(data: PathwayTemplateCreate, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    template = ClinicalPathwayTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates", response_model=List[PathwayTemplateResponse])
async def list_pathway_templates(specialty: Optional[str] = None, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    q = db.query(ClinicalPathwayTemplate).filter(ClinicalPathwayTemplate.is_active == True)
    if specialty:
        q = q.filter(ClinicalPathwayTemplate.specialty == specialty)
    return q.all()


# ── PATIENT CARE PLANS ─────────────────────────────────
@router.post("/from-template", response_model=CarePlanResponse, status_code=201)
async def start_care_plan_from_template(data: CarePlanCreateFromTemplate, db: Session = Depends(get_db),
                                         current_user: User = Depends(get_current_user)):
    template = db.query(ClinicalPathwayTemplate).filter(ClinicalPathwayTemplate.id == data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Pathway template not found")

    plan = PatientCarePlan(
        patient_id=data.patient_id,
        template_id=data.template_id,
        ipd_admission_id=data.ipd_admission_id,
        title=data.title or template.name,
        goals=template.goals,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    now = datetime.now(timezone.utc)
    for t in template.tasks:
        db.add(CarePlanTask(
            care_plan_id=plan.id,
            task_description=t.get("task", "Task"),
            task_type=t.get("type", "assessment"),
            due_at=now + timedelta(days=t.get("day_offset", 0)),
        ))
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/custom", response_model=CarePlanResponse, status_code=201)
async def start_custom_care_plan(data: CarePlanCreateCustom, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    plan = PatientCarePlan(**data.model_dump(), created_by=current_user.id)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/patient/{patient_id}", response_model=List[CarePlanResponse])
async def get_patient_care_plans(patient_id: int, active_only: bool = False, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    q = db.query(PatientCarePlan).filter(PatientCarePlan.patient_id == patient_id)
    if active_only:
        q = q.filter(PatientCarePlan.status == PathwayStatus.ACTIVE)
    return q.order_by(PatientCarePlan.started_at.desc()).all()


@router.get("/{plan_id}/tasks", response_model=List[CarePlanTaskResponse])
async def get_care_plan_tasks(plan_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    return db.query(CarePlanTask).filter(CarePlanTask.care_plan_id == plan_id).order_by(CarePlanTask.due_at).all()


@router.patch("/tasks/{task_id}", response_model=CarePlanTaskResponse)
async def update_task(task_id: int, data: CarePlanTaskUpdate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    task = db.query(CarePlanTask).filter(CarePlanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = data.status
    task.notes = data.notes
    if data.status == TaskStatus.DONE:
        task.completed_by = current_user.id
        task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{plan_id}/complete", response_model=CarePlanResponse)
async def complete_care_plan(plan_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    plan = db.query(PatientCarePlan).filter(PatientCarePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    plan.status = PathwayStatus.COMPLETED
    plan.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    return plan
