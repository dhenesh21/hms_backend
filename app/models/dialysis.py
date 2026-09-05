from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DialysisAccessType(str, enum.Enum):
    AV_FISTULA = "av_fistula"
    AV_GRAFT = "av_graft"
    CENTRAL_CATHETER = "central_catheter"
    PERITONEAL_CATHETER = "peritoneal_catheter"


class DialysisModality(str, enum.Enum):
    HEMODIALYSIS = "hemodialysis"
    PERITONEAL_DIALYSIS = "peritoneal_dialysis"
    CRRT = "crrt"   # continuous renal replacement therapy, for critical care


class DialysisSessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class DialysisPatientProfile(Base):
    """Standing renal-care profile — access details, dry weight target, modality.
    One per patient; sessions below reference it."""
    __tablename__ = "dialysis_patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True)
    nephrologist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    modality = Column(Enum(DialysisModality), default=DialysisModality.HEMODIALYSIS)
    access_type = Column(Enum(DialysisAccessType), nullable=False)
    access_site = Column(String(100))          # e.g. "left forearm"
    dry_weight_kg = Column(Float, nullable=True)
    frequency_per_week = Column(Integer, default=3)
    primary_renal_diagnosis = Column(String(300))
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DialysisSession(Base):
    __tablename__ = "dialysis_sessions"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("dialysis_patient_profiles.id"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(DialysisSessionStatus), default=DialysisSessionStatus.SCHEDULED)

    machine_id = Column(String(50), nullable=True)
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    pre_weight_kg = Column(Float, nullable=True)
    post_weight_kg = Column(Float, nullable=True)
    fluid_removed_ml = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    pre_bp_systolic = Column(Integer, nullable=True)
    pre_bp_diastolic = Column(Integer, nullable=True)
    post_bp_systolic = Column(Integer, nullable=True)
    post_bp_diastolic = Column(Integer, nullable=True)

    complications = Column(Text, nullable=True)   # hypotension, cramping, access issues etc
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
