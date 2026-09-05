from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class CriticalCareUnit(str, enum.Enum):
    ICU = "icu"
    CCU = "ccu"
    NICU = "nicu"


class CodeStatus(str, enum.Enum):
    FULL_CODE = "full_code"
    DNR = "dnr"                  # Do Not Resuscitate
    DNI = "dni"                  # Do Not Intubate
    COMFORT_CARE = "comfort_care"


class CriticalCareAdmission(Base):
    """
    One record per critical-care stay. Wraps an existing IPDAdmission with
    ICU/CCU/NICU-specific fields (roadmap: "ICU Admission", "CCU Admission",
    "NICU Admission") - it does not duplicate ward/bed/discharge tracking,
    that stays on IPDAdmission. This just adds what general IPD doesn't
    track: ventilator status, invasive lines, code status, step-down.
    """
    __tablename__ = "critical_care_admissions"

    id = Column(Integer, primary_key=True, index=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False, index=True)

    unit_type = Column(Enum(CriticalCareUnit), nullable=False)
    admission_reason = Column(Text, nullable=False)
    apache_ii_score = Column(Integer, nullable=True)  # severity scoring, adults ICU/CCU
    code_status = Column(Enum(CodeStatus), default=CodeStatus.FULL_CODE)

    on_ventilator = Column(Boolean, default=False)
    central_line = Column(Boolean, default=False)
    central_line_site = Column(String(100), nullable=True)
    urinary_catheter = Column(Boolean, default=False)
    arterial_line = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)  # still in critical care vs stepped down
    admitted_at = Column(DateTime(timezone=True), server_default=func.now())
    stepped_down_at = Column(DateTime(timezone=True), nullable=True)
    step_down_notes = Column(Text, nullable=True)

    admitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rounds = relationship("CriticalCareRound", back_populates="admission", order_by="CriticalCareRound.recorded_at.desc()")


class CriticalCareRound(Base):
    """
    Periodic (typically hourly) critical-care monitoring round - more
    granular than the general IPD VitalChart, includes ventilator settings,
    inotrope/vasopressor support, and sedation scoring.
    """
    __tablename__ = "critical_care_rounds"

    id = Column(Integer, primary_key=True, index=True)
    critical_care_admission_id = Column(Integer, ForeignKey("critical_care_admissions.id"), nullable=False)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    heart_rate = Column(Integer, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)

    # Ventilator settings - only relevant if on_ventilator
    ventilator_mode = Column(String(50), nullable=True)  # e.g. SIMV, AC, CPAP, PSV
    fio2_percent = Column(Float, nullable=True)
    peep = Column(Float, nullable=True)
    tidal_volume_ml = Column(Float, nullable=True)

    inotropes = Column(Text, nullable=True)  # free text: drug + dose, e.g. "Noradrenaline 0.1 mcg/kg/min"
    sedation_score = Column(Integer, nullable=True)  # RASS scale, -5 to +4
    gcs_score = Column(Integer, nullable=True)  # Glasgow Coma Scale, 3-15
    urine_output_ml = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)

    admission = relationship("CriticalCareAdmission", back_populates="rounds")
