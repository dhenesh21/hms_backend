from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CancerStage(str, enum.Enum):
    STAGE_0 = "stage_0"
    STAGE_I = "stage_i"
    STAGE_II = "stage_ii"
    STAGE_III = "stage_iii"
    STAGE_IV = "stage_iv"
    UNKNOWN = "unknown"


class TreatmentIntent(str, enum.Enum):
    CURATIVE = "curative"
    PALLIATIVE = "palliative"
    ADJUVANT = "adjuvant"
    NEOADJUVANT = "neoadjuvant"


class ChemoCycleStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ADMINISTERED = "administered"
    DELAYED = "delayed"
    SKIPPED = "skipped"


class OncologyCase(Base):
    """One case per cancer diagnosis for a patient (a patient could in principle
    have more than one primary over time). Tumor-board decisions and staging
    live here rather than on the general DiagnosisRecord, which isn't
    structured for stage/histology/protocol tracking."""
    __tablename__ = "oncology_cases"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    oncologist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    primary_site = Column(String(200), nullable=False)     # e.g. "breast", "colon"
    histology = Column(String(300), nullable=True)
    stage = Column(Enum(CancerStage), default=CancerStage.UNKNOWN)
    diagnosis_date = Column(Date, nullable=True)
    treatment_intent = Column(Enum(TreatmentIntent), nullable=True)

    tumor_board_reviewed = Column(Boolean, default=False)
    tumor_board_notes = Column(Text, nullable=True)
    chemo_protocol_name = Column(String(200), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChemoCycle(Base):
    __tablename__ = "chemo_cycles"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("oncology_cases.id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(Enum(ChemoCycleStatus), default=ChemoCycleStatus.SCHEDULED)

    drugs_administered = Column(JSON, default=list)   # [{"drug":"...", "dose":"...", "route":"..."}]
    body_surface_area = Column(String(20), nullable=True)   # for dose calc reference
    pre_cycle_labs_reviewed = Column(Boolean, default=False)
    toxicity_grade = Column(Integer, nullable=True)    # CTCAE-style 0-5
    adverse_events = Column(Text, nullable=True)
    delay_reason = Column(Text, nullable=True)

    administered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OncologyFollowUp(Base):
    """Surveillance visits after active treatment — response assessment, imaging review."""
    __tablename__ = "oncology_follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("oncology_cases.id"), nullable=False)
    visit_date = Column(Date, server_default=func.current_date())
    response_assessment = Column(String(100), nullable=True)  # complete_response, partial, stable, progression
    imaging_reviewed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    next_follow_up_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
