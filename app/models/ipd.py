from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class WardType(str, enum.Enum):
    GENERAL = "general"
    PRIVATE = "private"
    SEMI_PRIVATE = "semi_private"
    ICU = "icu"
    CCU = "ccu"
    NICU = "nicu"
    HDU = "hdu"
    EMERGENCY = "emergency"
    MATERNITY = "maternity"


class BedStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


class AdmissionType(str, enum.Enum):
    ELECTIVE = "elective"
    EMERGENCY = "emergency"
    TRANSFER = "transfer"
    DAY_CARE = "day_care"


class IPDStatus(str, enum.Enum):
    ADMITTED = "admitted"
    TRANSFERRED = "transferred"
    DISCHARGED = "discharged"
    ABSCONDED = "absconded"
    LAMA = "lama"       # Left Against Medical Advice
    EXPIRED = "expired"


class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    ward_type = Column(Enum(WardType), nullable=False)
    floor = Column(Integer, default=1)
    total_beds = Column(Integer, nullable=False)
    available_beds = Column(Integer, nullable=False)
    charge_per_day = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    beds = relationship("Bed", back_populates="ward")


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    bed_number = Column(String(20), nullable=False, unique=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    bed_type = Column(String(50), default="standard")
    status = Column(Enum(BedStatus), default=BedStatus.AVAILABLE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ward = relationship("Ward", back_populates="beds")
    admissions = relationship("IPDAdmission", back_populates="bed")


class IPDAdmission(Base):
    __tablename__ = "ipd_admissions"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    bed_id = Column(Integer, ForeignKey("beds.id"))
    ward_id = Column(Integer, ForeignKey("wards.id"))
    admitting_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"))
    primary_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"))

    admission_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_discharge_date = Column(Date)
    discharge_date = Column(DateTime(timezone=True))
    admission_type = Column(Enum(AdmissionType), default=AdmissionType.ELECTIVE)
    status = Column(Enum(IPDStatus), default=IPDStatus.ADMITTED)

    # Clinical
    chief_complaint = Column(Text)
    diagnosis_at_admission = Column(Text)
    discharge_diagnosis = Column(Text)
    discharge_summary = Column(Text)
    discharge_instructions = Column(Text)
    condition_at_discharge = Column(String(100))

    # Transfer info
    transferred_from = Column(String(200))
    transferred_to = Column(String(200))
    transfer_reason = Column(Text)

    # Insurance
    insurance_provider = Column(String(200))
    insurance_policy_number = Column(String(100))
    tpa_name = Column(String(200))

    remarks = Column(Text)
    admitted_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient")
    bed = relationship("Bed", back_populates="admissions")
    ward = relationship("Ward")
    nursing_notes = relationship("NursingNote", back_populates="admission")
    progress_notes = relationship("DailyProgressNote", back_populates="admission")
    vital_charts = relationship("VitalChart", back_populates="admission")


class NursingNote(Base):
    __tablename__ = "nursing_notes"

    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    nurse_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note_type = Column(String(50), default="general")  # general, medication, observation
    note = Column(Text, nullable=False)
    shift = Column(String(20))  # morning, afternoon, night
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    admission = relationship("IPDAdmission", back_populates="nursing_notes")


class DailyProgressNote(Base):
    __tablename__ = "daily_progress_notes"

    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    note_date = Column(Date, server_default=func.current_date())
    subjective = Column(Text)    # Patient complaints
    objective = Column(Text)     # Exam findings
    assessment = Column(Text)    # Doctor's assessment
    plan = Column(Text)          # Treatment plan
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    admission = relationship("IPDAdmission", back_populates="progress_notes")


class VitalChart(Base):
    __tablename__ = "vital_charts"

    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    temperature = Column(Float)
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    pulse_rate = Column(Integer)
    respiratory_rate = Column(Integer)
    oxygen_saturation = Column(Float)
    blood_sugar = Column(Float)
    urine_output_ml = Column(Integer)
    pain_score = Column(Integer)   # 0-10
    gcs_score = Column(Integer)    # Glasgow Coma Scale
    notes = Column(Text)

    admission = relationship("IPDAdmission", back_populates="vital_charts")
