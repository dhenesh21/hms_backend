from pydantic import BaseModel
from typing import Optional
from app.models.report_template import ReportDepartment


class ReportTemplateCreate(BaseModel):
    department: ReportDepartment
    category: str
    template_name: str
    findings_template: str
    impression_template: Optional[str] = None


class ReportTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    findings_template: Optional[str] = None
    impression_template: Optional[str] = None
    is_active: Optional[bool] = None


class ReportTemplateResponse(BaseModel):
    id: int
    department: ReportDepartment
    category: str
    template_name: str
    findings_template: str
    impression_template: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True
