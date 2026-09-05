from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ASAGrade(str, enum.Enum):
    ASA_I = "asa_i"       # normal healthy patient
    ASA_II = "asa_ii"     # mild systemic disease
    ASA_III = "asa_iii"   # severe systemic disease
    ASA_IV = "asa_iv"     # life-threatening
    ASA_V = "asa_v"       # moribund, not expected to survive without surgery
    ASA_VI = "asa_vi"     # brain-dead, organ donor


class FastingStatus(str, enum.Enum):
    CONFIRMED_NPO = "confirmed_npo"
    NOT_CONFIRMED = "not_confirmed"
    EMERGENCY_FULL_STOMACH = "emergency_full_stomach"


class PreAnesthesiaAssessment(Base):
    """Pre-op anesthesia check-up (PAC) — done before a Surgery is confirmed for OT."""
    __tablename__ = "pre_anesthesia_assessments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False, index=True)
    anesthesiologist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    asa_grade = Column(Enum(ASAGrade), nullable=True)
    airway_assessment = Column(Text)          # Mallampati score, neck mobility etc
    fasting_status = Column(Enum(FastingStatus), default=FastingStatus.NOT_CONFIRMED)
    comorbidities_reviewed = Column(Boolean, default=False)
    allergies_reviewed = Column(Boolean, default=False)   # cross-checked against PatientAllergy
    previous_anesthesia_issues = Column(Text)
    planned_technique = Column(String(100))    # matches AnesthesiaType on Surgery
    investigations_reviewed = Column(Text)
    fitness_for_anesthesia = Column(Boolean, nullable=True)   # null = pending decision
    remarks = Column(Text)

    assessed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnesthesiaRecord(Base):
    """Intra-operative anesthesia chart — vitals + drugs given during the case."""
    __tablename__ = "anesthesia_records"

    id = Column(Integer, primary_key=True, index=True)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False, unique=True, index=True)
    anesthesiologist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    technique_used = Column(String(100))
    induction_time = Column(DateTime(timezone=True), nullable=True)
    intubation_time = Column(DateTime(timezone=True), nullable=True)
    extubation_time = Column(DateTime(timezone=True), nullable=True)

    drugs_administered = Column(JSON, default=list)   # [{"drug":"Propofol","dose":"2mg/kg","time":"..."}]
    fluids_administered = Column(JSON, default=list)  # [{"fluid":"RL","volume_ml":500}]
    blood_products_used = Column(JSON, default=list)

    intraop_events = Column(Text)     # complications, hemodynamic instability etc
    total_blood_loss_ml = Column(Integer, nullable=True)
    total_urine_output_ml = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AnesthesiaVital(Base):
    """Periodic (typically 5-min) intra-op vitals — the anesthesia chart trend line."""
    __tablename__ = "anesthesia_vitals"

    id = Column(Integer, primary_key=True, index=True)
    anesthesia_record_id = Column(Integer, ForeignKey("anesthesia_records.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    heart_rate = Column(Integer, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    spo2 = Column(Float, nullable=True)
    etco2 = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
