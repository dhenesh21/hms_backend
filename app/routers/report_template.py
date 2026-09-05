from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.report_template import ReportTemplate, ReportDepartment
from app.models.user import User
from app.schemas.report_template import ReportTemplateCreate, ReportTemplateUpdate, ReportTemplateResponse

router = APIRouter(prefix="/report-templates", tags=["Diagnostic Reporting Templates"])


@router.post("", response_model=ReportTemplateResponse, status_code=201)
async def create_template(
    data: ReportTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = ReportTemplate(**data.model_dump(), created_by=current_user.id)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("", response_model=list[ReportTemplateResponse])
async def list_templates(
    department: Optional[ReportDepartment] = Query(None),
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ReportTemplate)
    if department:
        q = q.filter(ReportTemplate.department == department)
    if category:
        q = q.filter(ReportTemplate.category == category)
    if active_only:
        q = q.filter(ReportTemplate.is_active == True)  # noqa: E712
    return q.order_by(ReportTemplate.template_name).all()


@router.get("/{template_id}", response_model=ReportTemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    return template


@router.put("/{template_id}", response_model=ReportTemplateResponse)
async def update_template(
    template_id: int,
    data: ReportTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete: mark inactive rather than removing the row, so historical
    reports that reference this template_id via report submissions stay intact."""
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    template.is_active = False
    db.commit()
    return None
