from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON, Time)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class MedicationFrequency(str, enum.Enum):
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THRICE_DAILY = "thrice_daily"
    FOUR_TIMES = "four_times_daily"
    EVERY_4H = "every_4_hours"
    EVERY_6H = "every_6_hours"
    EVERY_8H = "every_8_hours"
    EVERY_12H = "every_12_hours"
    SOS = "sos"
    STAT = "stat"


class AdministrationStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    GIVEN = "given"
    MISSED = "missed"
    REFUSED = "refused"
    HELD = "held"
    NA = "not_applicable"


class AssessmentType(str, enum.Enum):
    ADMISSION = "admission"
    DAILY = "daily"
    DISCHARGE = "discharge"
    FALL_RISK = "fall_risk"
    PAIN = "pain"
    NUTRITIONAL = "nutritional"
    PRESSURE_ULCER = "pressure_ulcer"


class CarePlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class MedicationAdministrationRecord(Base):
    """MAR - tracks every scheduled dose for admitted patients"""
    __tablename__ = "medication_administration_records"

    id = Column(Integer, primary_key=True, index=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    # Drug info
    drug_name = Column(String(200), nullable=False)
    generic_name = Column(String(200))
    drug_id = Column(Integer, ForeignKey("drug_master.id"), nullable=True)
    dose = Column(String(100), nullable=False)
    route = Column(String(50), default="oral")
    frequency = Column(Enum(MedicationFrequency), nullable=False)
    scheduled_times = Column(JSON, default=list)  # ["06:00", "14:00", "22:00"]

    # Order info
    ordered_by = Column(Integer, ForeignKey("doctor_profiles.id"))
    order_date = Column(Date, server_default=func.current_date())
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    instructions = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    administrations = relationship("MedicationAdministration", back_populates="mar")


class MedicationAdministration(Base):
    """Individual dose given record"""
    __tablename__ = "medication_administrations"

    id = Column(Integer, primary_key=True, index=True)
    mar_id = Column(Integer, ForeignKey("medication_administration_records.id"), nullable=False)
    scheduled_datetime = Column(DateTime(timezone=True), nullable=False)
    administered_datetime = Column(DateTime(timezone=True))
    status = Column(Enum(AdministrationStatus), default=AdministrationStatus.SCHEDULED)
    administered_by = Column(Integer, ForeignKey("users.id"))
    dose_given = Column(String(100))
    remarks = Column(Text)
    reason_not_given = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    mar = relationship("MedicationAdministrationRecord", back_populates="administrations")


class NursingAssessment(Base):
    __tablename__ = "nursing_assessments"

    id = Column(Integer, primary_key=True, index=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    assessment_date = Column(DateTime(timezone=True), server_default=func.now())
    assessed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # General assessment
    general_condition = Column(String(100))      # good, fair, poor, critical
    consciousness = Column(String(100))           # conscious, drowsy, unconscious
    orientation = Column(String(200))             # oriented to time/place/person

    # Pain assessment
    pain_score = Column(Integer)                  # 0-10 VAS
    pain_location = Column(String(200))
    pain_character = Column(String(200))          # sharp, dull, throbbing
    pain_relieving_factors = Column(Text)

    # Fall risk (Morse Fall Scale)
    fall_risk_score = Column(Integer)
    fall_risk_level = Column(String(20))          # low, moderate, high

    # Pressure ulcer (Braden Scale)
    braden_score = Column(Integer)
    pressure_ulcer_risk = Column(String(20))
    existing_wounds = Column(Text)

    # Nutritional
    nutritional_status = Column(String(50))
    diet_type = Column(String(100))
    allergies_noted = Column(Text)

    # Systems review
    respiratory = Column(Text)
    cardiovascular = Column(Text)
    neurological = Column(Text)
    gastrointestinal = Column(Text)
    genitourinary = Column(Text)
    musculoskeletal = Column(Text)
    integumentary = Column(Text)  # skin assessment

    # IV lines, tubes, drains
    iv_access = Column(Text)
    catheters = Column(Text)
    drains = Column(Text)
    oxygen_therapy = Column(Text)

    additional_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CarePlan(Base):
    __tablename__ = "care_plans"

    id = Column(Integer, primary_key=True, index=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    problem_statement = Column(Text, nullable=False)
    nursing_diagnosis = Column(Text)
    goal = Column(Text, nullable=False)
    interventions = Column(JSON, default=list)   # list of interventions
    expected_outcome = Column(Text)
    status = Column(Enum(CarePlanStatus), default=CarePlanStatus.ACTIVE)
    target_date = Column(Date)
    achieved_date = Column(Date)
    evaluation_notes = Column(Text)
    priority = Column(String(20), default="medium")  # high, medium, low
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    interventions_done = relationship("CareIntervention", back_populates="care_plan")


class CareIntervention(Base):
    """Records each intervention performed against a care plan"""
    __tablename__ = "care_interventions"

    id = Column(Integer, primary_key=True, index=True)
    care_plan_id = Column(Integer, ForeignKey("care_plans.id"), nullable=False)
    intervention = Column(Text, nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    performed_by = Column(Integer, ForeignKey("users.id"))
    outcome = Column(Text)
    patient_response = Column(Text)

    care_plan = relationship("CarePlan", back_populates="interventions_done")


class ShiftHandover(Base):
    __tablename__ = "shift_handovers"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    shift_date = Column(Date, nullable=False)
    from_shift = Column(String(20), nullable=False)  # morning, afternoon, night
    to_shift = Column(String(20), nullable=False)
    handover_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    received_by = Column(Integer, ForeignKey("users.id"))

    # General ward status
    total_patients = Column(Integer, default=0)
    critical_patients = Column(Integer, default=0)
    new_admissions = Column(Integer, default=0)
    discharges = Column(Integer, default=0)

    # Handover notes
    general_notes = Column(Text)
    pending_tasks = Column(JSON, default=list)
    critical_alerts = Column(JSON, default=list)
    equipment_issues = Column(Text)

    patient_summaries = Column(JSON, default=list)  # [{patient_id, uhid, name, summary}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
