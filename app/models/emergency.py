from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Enum,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class TriageLevel(str, enum.Enum):
    """Standard 5-level Emergency Severity Index (ESI), 1 = most critical."""
    LEVEL_1_RESUSCITATION = "level_1_resuscitation"
    LEVEL_2_EMERGENT = "level_2_emergent"
    LEVEL_3_URGENT = "level_3_urgent"
    LEVEL_4_LESS_URGENT = "level_4_less_urgent"
    LEVEL_5_NON_URGENT = "level_5_non_urgent"


class ERVisitStatus(str, enum.Enum):
    WAITING = "waiting"
    IN_TRIAGE = "in_triage"
    IN_TREATMENT = "in_treatment"
    ADMITTED = "admitted"
    DISCHARGED = "discharged"
    REFERRED_OUT = "referred_out"
    DECEASED = "deceased"
    LEFT_WITHOUT_TREATMENT = "left_without_treatment"


class ArrivalMode(str, enum.Enum):
    WALK_IN = "walk_in"
    AMBULANCE = "ambulance"
    POLICE = "police"
    REFERRED = "referred"
    BROUGHT_DEAD = "brought_dead"


class ERVisit(Base):
    """
    One record per ER encounter. Covers "ER Registration" +
    "Emergency Admission" from the roadmap; admission to an actual IPD bed
    is tracked separately via ipd_admission_id once the patient is admitted.
    """
    __tablename__ = "er_visits"

    id = Column(Integer, primary_key=True, index=True)

    er_number = Column(String(20), unique=True, index=True, nullable=False)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    arrival_time = Column(DateTime(timezone=True), server_default=func.now())
    arrival_mode = Column(Enum(ArrivalMode), default=ArrivalMode.WALK_IN)
    brought_by = Column(String(200), nullable=True)  # name/relation, or police station / ambulance service

    chief_complaint = Column(Text, nullable=False)
    status = Column(Enum(ERVisitStatus), default=ERVisitStatus.WAITING)

    # Trauma / Accident / MLC register fields
    is_mlc = Column(Boolean, default=False)  # Medico-Legal Case
    mlc_number = Column(String(30), nullable=True)
    is_trauma = Column(Boolean, default=False)
    incident_type = Column(String(100), nullable=True)  # e.g. RTA, fall, assault, burn
    incident_datetime = Column(DateTime(timezone=True), nullable=True)
    police_informed = Column(Boolean, default=False)
    police_station = Column(String(200), nullable=True)
    fir_number = Column(String(50), nullable=True)

    attending_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)

    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    outcome_notes = Column(Text, nullable=True)
    discharge_time = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    triage = relationship("ERTriage", back_populates="er_visit", uselist=False)
    treatments = relationship("EREmergencyTreatment", back_populates="er_visit")


class ERTriage(Base):
    """Triage assessment - vitals + severity level, taken at intake."""
    __tablename__ = "er_triage"

    id = Column(Integer, primary_key=True, index=True)
    er_visit_id = Column(Integer, ForeignKey("er_visits.id"), nullable=False)

    triage_level = Column(Enum(TriageLevel), nullable=False)
    triage_time = Column(DateTime(timezone=True), server_default=func.now())
    triaged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    temperature = Column(Float, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    pulse_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Float, nullable=True)
    glasgow_coma_scale = Column(Integer, nullable=True)  # 3-15
    pain_score = Column(Integer, nullable=True)  # 0-10

    notes = Column(Text, nullable=True)

    er_visit = relationship("ERVisit", back_populates="triage")


class EREmergencyTreatment(Base):
    """Treatment / intervention notes given during the ER stay."""
    __tablename__ = "er_treatments"

    id = Column(Integer, primary_key=True, index=True)
    er_visit_id = Column(Integer, ForeignKey("er_visits.id"), nullable=False)

    treatment_time = Column(DateTime(timezone=True), server_default=func.now())
    treatment_given = Column(Text, nullable=False)
    medication_given = Column(Text, nullable=True)
    procedure_performed = Column(Text, nullable=True)
    given_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    er_visit = relationship("ERVisit", back_populates="treatments")
