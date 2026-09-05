from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class FormTemplateCreate(BaseModel):
    name: str
    department: Optional[str] = None
    category: Optional[str] = None
    schema_json: List[dict]


class FormTemplateResponse(BaseModel):
    id: int
    name: str
    department: Optional[str]
    category: Optional[str]
    version: int
    schema_json: Any
    is_active: bool

    class Config:
        from_attributes = True


class FormSubmissionCreate(BaseModel):
    template_id: int
    patient_id: int
    source: Optional[str] = None
    source_id: Optional[int] = None
    data_json: dict


class FormSubmissionUpdate(BaseModel):
    data_json: Optional[dict] = None
    is_locked: Optional[bool] = None


class FormSubmissionResponse(BaseModel):
    id: int
    template_id: int
    patient_id: int
    source: Optional[str]
    source_id: Optional[int]
    data_json: Any
    submitted_by: Optional[int]
    is_locked: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
