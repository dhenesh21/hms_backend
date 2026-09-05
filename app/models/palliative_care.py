from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CareSetting(str, enum.Enum):
    INPATIENT = "inpatient"
    HOME_BASED = "home_based"
    OUTPATIENT_CLINIC = "outpatient_clinic"


class PalliativeCarePlan(Base):
    __tablename__ = "palliative_care_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    primary_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    primary_diagnosis = Column(String(300), nullable=False)
    care_setting = Column(Enum(CareSetting), default=CareSetting.INPATIENT)
    goals_of_care = Column(Text)               # comfort-focused goals, discussed with family
    code_status = Column(String(50), nullable=True)   # DNR/DNI etc — mirrors critical_care.CodeStatus concept
    primary_caregiver_name = Column(String(200), nullable=True)
    primary_caregiver_contact = Column(String(20), nullable=True)

    psychosocial_support_needed = Column(Boolean, default=False)
    spiritual_support_needed = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closure_reason = Column(String(100), nullable=True)   # symptom_resolved, transferred, deceased
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SymptomAssessment(Base):
    """Palliative symptom tracking (ESAS-style multi-symptom scoring, not just pain)."""
    __tablename__ = "palliative_symptom_assessments"

    id = Column(Integer, primary_key=True, index=True)
    care_plan_id = Column(Integer, ForeignKey("palliative_care_plans.id"), nullable=False)
    assessed_at = Column(DateTime(timezone=True), server_default=func.now())
    assessed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    symptom_scores = Column(JSON, default=dict)   # {"pain":4,"nausea":1,"fatigue":6,"appetite":3,...} 0-10 each
    interventions_given = Column(Text)
    family_meeting_held = Column(Boolean, default=False)
    notes = Column(Text)
