from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON, Date)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class RehabPlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class PhysiotherapyPlan(Base):
    __tablename__ = "physiotherapy_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    referring_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    diagnosis = Column(String(300), nullable=False)
    goals = Column(JSON, default=list)
    plan_details = Column(Text)          # exercises, modalities prescribed
    frequency_per_week = Column(Integer, default=3)
    total_sessions_planned = Column(Integer, nullable=True)
    status = Column(Enum(RehabPlanStatus), default=RehabPlanStatus.ACTIVE)

    started_on = Column(Date, server_default=func.current_date())
    ended_on = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PhysiotherapySession(Base):
    __tablename__ = "physiotherapy_sessions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("physiotherapy_plans.id"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.SCHEDULED)

    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activities_performed = Column(Text)
    pain_score_before = Column(Integer, nullable=True)
    pain_score_after = Column(Integer, nullable=True)
    functional_improvement_notes = Column(Text)
    patient_tolerance = Column(String(100), nullable=True)   # good, fair, poor

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
