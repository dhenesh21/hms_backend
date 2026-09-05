from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PathwayStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    MISSED = "missed"
    SKIPPED = "skipped"


class ClinicalPathwayTemplate(Base):
    """Standard care pathway (e.g. 'Post-CABG Recovery', 'Stroke Protocol', 'Dialysis Cycle')."""
    __tablename__ = "clinical_pathway_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    specialty = Column(String(100))
    description = Column(Text)
    goals = Column(JSON, default=list)         # ["Pain < 3/10 by Day 2", ...]
    tasks = Column(JSON, default=list)         # [{"day_offset":0,"task":"...", "type":"order/assessment/education"}]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatientCarePlan(Base):
    """A pathway/care-plan instance applied to a specific patient episode."""
    __tablename__ = "patient_care_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("clinical_pathway_templates.id"), nullable=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    title = Column(String(200), nullable=False)
    status = Column(Enum(PathwayStatus), default=PathwayStatus.ACTIVE)
    goals = Column(JSON, default=list)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    target_end_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CarePlanTask(Base):
    __tablename__ = "care_plan_tasks"

    id = Column(Integer, primary_key=True, index=True)
    care_plan_id = Column(Integer, ForeignKey("patient_care_plans.id"), nullable=False)
    task_description = Column(Text, nullable=False)
    task_type = Column(String(50))          # order, assessment, education, review
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
