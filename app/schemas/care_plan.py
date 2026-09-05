from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.care_plan import PathwayStatus, TaskStatus


class PathwayTemplateCreate(BaseModel):
    name: str
    specialty: Optional[str] = None
    description: Optional[str] = None
    goals: List[str] = []
    tasks: List[dict] = []


class PathwayTemplateResponse(BaseModel):
    id: int
    name: str
    specialty: Optional[str]
    description: Optional[str]
    goals: Any
    tasks: Any
    is_active: bool

    class Config:
        from_attributes = True


class CarePlanCreateFromTemplate(BaseModel):
    patient_id: int
    template_id: int
    ipd_admission_id: Optional[int] = None
    title: Optional[str] = None


class CarePlanCreateCustom(BaseModel):
    patient_id: int
    title: str
    ipd_admission_id: Optional[int] = None
    goals: List[str] = []


class CarePlanResponse(BaseModel):
    id: int
    patient_id: int
    template_id: Optional[int]
    title: str
    status: PathwayStatus
    goals: Any
    started_at: datetime
    target_end_date: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CarePlanTaskResponse(BaseModel):
    id: int
    care_plan_id: int
    task_description: str
    task_type: Optional[str]
    due_at: Optional[datetime]
    status: TaskStatus
    notes: Optional[str]

    class Config:
        from_attributes = True


class CarePlanTaskUpdate(BaseModel):
    status: TaskStatus
    notes: Optional[str] = None
