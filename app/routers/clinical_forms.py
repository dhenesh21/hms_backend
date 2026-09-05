from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.clinical_forms import FormTemplate, FormSubmission
from app.models.user import User
from app.schemas.clinical_forms import (
    FormTemplateCreate, FormTemplateResponse,
    FormSubmissionCreate, FormSubmissionUpdate, FormSubmissionResponse,
)

router = APIRouter(prefix="/clinical-forms", tags=["Clinical Forms / Form Builder"])


def _validate_against_schema(schema_json: list, data_json: dict):
    missing = [f["key"] for f in schema_json if f.get("required") and f["key"] not in data_json]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")


# ── TEMPLATES (Form Builder) ───────────────────────────
@router.post("/templates", response_model=FormTemplateResponse, status_code=201)
async def create_template(data: FormTemplateCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    template = FormTemplate(**data.model_dump(), created_by=current_user.id)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates", response_model=List[FormTemplateResponse])
async def list_templates(department: Optional[str] = None, category: Optional[str] = None,
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(FormTemplate).filter(FormTemplate.is_active == True)
    if department:
        q = q.filter(FormTemplate.department == department)
    if category:
        q = q.filter(FormTemplate.category == category)
    return q.all()


@router.put("/templates/{template_id}", response_model=FormTemplateResponse)
async def update_template(template_id: int, data: FormTemplateCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Updating a template bumps its version so historical submissions stay interpretable."""
    template = db.query(FormTemplate).filter(FormTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in data.model_dump().items():
        setattr(template, k, v)
    template.version += 1
    db.commit()
    db.refresh(template)
    return template


# ── SUBMISSIONS ────────────────────────────────────────
@router.post("/submissions", response_model=FormSubmissionResponse, status_code=201)
async def submit_form(data: FormSubmissionCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    template = db.query(FormTemplate).filter(FormTemplate.id == data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    _validate_against_schema(template.schema_json, data.data_json)

    submission = FormSubmission(**data.model_dump(), submitted_by=current_user.id)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/submissions", response_model=List[FormSubmissionResponse])
async def list_submissions(patient_id: Optional[int] = None, template_id: Optional[int] = None,
                            source: Optional[str] = None, source_id: Optional[int] = None,
                            db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(FormSubmission)
    if patient_id:
        q = q.filter(FormSubmission.patient_id == patient_id)
    if template_id:
        q = q.filter(FormSubmission.template_id == template_id)
    if source:
        q = q.filter(FormSubmission.source == source)
    if source_id:
        q = q.filter(FormSubmission.source_id == source_id)
    return q.order_by(FormSubmission.created_at.desc()).all()


@router.patch("/submissions/{submission_id}", response_model=FormSubmissionResponse)
async def update_submission(submission_id: int, data: FormSubmissionUpdate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    submission = db.query(FormSubmission).filter(FormSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.is_locked:
        raise HTTPException(status_code=400, detail="Submission is locked and cannot be edited")

    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(submission, k, v)
    db.commit()
    db.refresh(submission)
    return submission
