from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class TreatmentType(str, enum.Enum):
    IUI = "iui"
    IVF = "ivf"
    ICSI = "icsi"
    FET = "fet"           # frozen embryo transfer
    OVULATION_INDUCTION = "ovulation_induction"
    FERTILITY_PRESERVATION = "fertility_preservation"


class FertilityCycleStatus(str, enum.Enum):
    PLANNED = "planned"
    STIMULATION = "stimulation"
    RETRIEVAL = "retrieval"
    TRANSFER = "transfer"
    LUTEAL_SUPPORT = "luteal_support"
    PREGNANCY_TEST_DUE = "pregnancy_test_due"
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"
    CANCELLED = "cancelled"


class FertilityPatientProfile(Base):
    """Standing fertility-care record for a couple/individual seeking treatment.
    `partner_name`/`partner_patient_id` covers the couple without requiring a
    second full Patient record if the partner isn't otherwise a hospital patient."""
    __tablename__ = "fertility_patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True)
    fertility_specialist_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    partner_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    partner_name = Column(String(200), nullable=True)

    diagnosis = Column(String(300), nullable=True)      # e.g. "unexplained infertility", "male factor"
    amh_level = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FertilityCycle(Base):
    __tablename__ = "fertility_cycles"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("fertility_patient_profiles.id"), nullable=False)
    treatment_type = Column(Enum(TreatmentType), nullable=False)
    status = Column(Enum(FertilityCycleStatus), default=FertilityCycleStatus.PLANNED)

    cycle_start_date = Column(Date, nullable=True)
    stimulation_protocol = Column(String(200), nullable=True)

    eggs_retrieved = Column(Integer, nullable=True)
    embryos_created = Column(Integer, nullable=True)
    embryos_transferred = Column(Integer, nullable=True)
    embryos_frozen = Column(Integer, nullable=True)

    transfer_date = Column(Date, nullable=True)
    pregnancy_test_date = Column(Date, nullable=True)
    pregnancy_test_result = Column(String(20), nullable=True)   # positive, negative, pending

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FertilityMonitoringVisit(Base):
    """Follicle-tracking / hormone-monitoring visits during a stimulation cycle."""
    __tablename__ = "fertility_monitoring_visits"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("fertility_cycles.id"), nullable=False)
    visit_date = Column(Date, server_default=func.current_date())
    day_of_cycle = Column(Integer, nullable=True)

    follicle_counts = Column(JSON, nullable=True)     # {"left": 5, "right": 4} or per-size breakdown
    endometrial_thickness_mm = Column(Float, nullable=True)
    estradiol_level = Column(Float, nullable=True)
    lh_level = Column(Float, nullable=True)
    medication_adjustment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
