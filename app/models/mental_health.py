from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class RiskLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    IMMINENT = "imminent"


class MentalHealthPlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class PsychiatricAssessment(Base):
    """
    Initial/periodic psychiatric evaluation. Deliberately does NOT duplicate
    EMR's general clinical documentation — this is specialty-specific
    (risk screening, mental status exam) that a general ClinicalDocument
    row wouldn't structure correctly. Access to this table should be
    restricted more tightly than general records at the application/role
    layer — flagged in the roadmap, not enforced by a new mechanism here
    since role-based access is already handled by the existing RBAC system
    (UserRole + require_roles), not by this module reinventing it.
    """
    __tablename__ = "psychiatric_assessments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    psychiatrist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    source = Column(String(50), nullable=True)     # opd, ipd, emergency
    source_id = Column(Integer, nullable=True)

    presenting_complaint = Column(Text, nullable=False)
    mental_status_exam = Column(Text, nullable=True)
    risk_self_harm = Column(Enum(RiskLevel), default=RiskLevel.NONE)
    risk_to_others = Column(Enum(RiskLevel), default=RiskLevel.NONE)
    provisional_diagnosis = Column(String(300), nullable=True)
    icd_code = Column(String(20), nullable=True)

    safety_plan_created = Column(Boolean, default=False)
    family_involved = Column(Boolean, default=False)

    assessed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MentalHealthCarePlan(Base):
    __tablename__ = "mental_health_care_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("psychiatric_assessments.id"), nullable=True)
    psychiatrist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    diagnosis = Column(String(300), nullable=False)
    treatment_modalities = Column(JSON, default=list)   # ["medication","therapy","group_session"]
    goals = Column(JSON, default=list)
    status = Column(Enum(MentalHealthPlanStatus), default=MentalHealthPlanStatus.ACTIVE)

    next_review_date = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)


class TherapySession(Base):
    __tablename__ = "therapy_sessions"

    id = Column(Integer, primary_key=True, index=True)
    care_plan_id = Column(Integer, ForeignKey("mental_health_care_plans.id"), nullable=False)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_type = Column(String(100), nullable=True)   # individual, group, family, cbt
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    attended = Column(Boolean, nullable=True)
    session_notes = Column(Text, nullable=True)
    risk_reassessed = Column(Enum(RiskLevel), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
