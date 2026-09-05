from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PainType(str, enum.Enum):
    ACUTE = "acute"
    CHRONIC = "chronic"
    CANCER_RELATED = "cancer_related"
    POST_SURGICAL = "post_surgical"
    NEUROPATHIC = "neuropathic"


class PainManagementPlan(Base):
    __tablename__ = "pain_management_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    managing_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    pain_type = Column(Enum(PainType), nullable=False)
    pain_location = Column(String(200))
    baseline_pain_score = Column(Integer, nullable=True)   # 0-10
    treatment_plan = Column(Text)          # pharmacological + non-pharmacological approach
    target_pain_score = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)


class PainAssessment(Base):
    """Periodic pain score recording — the vital-sign-style trend line for a pain plan."""
    __tablename__ = "pain_assessments"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("pain_management_plans.id"), nullable=False)
    assessed_at = Column(DateTime(timezone=True), server_default=func.now())
    assessed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    pain_score = Column(Integer, nullable=False)   # 0-10
    pain_character = Column(String(100), nullable=True)   # sharp, dull, burning, throbbing
    interventions_given = Column(JSON, default=list)       # [{"drug":"...", "dose":"...", "route":"..."}]
    response_after_intervention = Column(String(100), nullable=True)
    side_effects_noted = Column(Text)
    notes = Column(Text)
