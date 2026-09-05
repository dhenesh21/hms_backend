from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, Time, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class OTStatus(str, enum.Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    IN_USE = "in_use"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


class SurgeryStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    PRE_OP = "pre_op"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class AnesthesiaType(str, enum.Enum):
    GENERAL = "general"
    LOCAL = "local"
    REGIONAL = "regional"
    SPINAL = "spinal"
    EPIDURAL = "epidural"
    SEDATION = "sedation"


class OperationTheatre(Base):
    __tablename__ = "operation_theatres"

    id = Column(Integer, primary_key=True, index=True)
    ot_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    ot_type = Column(String(100))   # Major, Minor, Emergency, Cardiac
    floor = Column(Integer)
    status = Column(Enum(OTStatus), default=OTStatus.AVAILABLE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    surgeries = relationship("Surgery", back_populates="ot")


class Surgery(Base):
    __tablename__ = "surgeries"

    id = Column(Integer, primary_key=True, index=True)
    surgery_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"))
    ot_id = Column(Integer, ForeignKey("operation_theatres.id"), nullable=False)

    # Scheduling
    surgery_date = Column(Date, nullable=False)
    scheduled_start_time = Column(String(10), nullable=False)
    scheduled_end_time = Column(String(10))
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)

    status = Column(Enum(SurgeryStatus), default=SurgeryStatus.SCHEDULED)

    # Surgical team
    primary_surgeon_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    assistant_surgeon_ids = Column(JSON, default=list)
    anesthesiologist_id = Column(Integer, ForeignKey("doctor_profiles.id"))
    scrub_nurse_id = Column(Integer, ForeignKey("users.id"))

    # Procedure
    procedure_name = Column(String(500), nullable=False)
    icd_procedure_code = Column(String(20))
    anesthesia_type = Column(Enum(AnesthesiaType))
    surgery_type = Column(String(100))  # Elective, Emergency, Diagnostic

    # Pre-op
    pre_op_diagnosis = Column(Text)
    pre_op_notes = Column(Text)
    pre_op_checklist = Column(JSON, default=dict)
    pre_op_completed_at = Column(DateTime(timezone=True))
    pre_op_completed_by = Column(Integer, ForeignKey("users.id"))

    # Intra-op
    intra_op_notes = Column(Text)
    complications = Column(Text)
    blood_loss_ml = Column(Integer)
    fluids_given_ml = Column(Integer)
    blood_transfusion_units = Column(Integer)
    implants_used = Column(Text)
    specimens_sent = Column(Text)

    # Post-op
    post_op_diagnosis = Column(Text)
    post_op_notes = Column(Text)
    post_op_instructions = Column(Text)
    recovery_room_entry = Column(DateTime(timezone=True))
    recovery_room_exit = Column(DateTime(timezone=True))
    post_op_condition = Column(String(100))

    cancelled_reason = Column(Text)
    scheduled_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient")
    ot = relationship("OperationTheatre", back_populates="surgeries")
    consumables = relationship("OTConsumable", back_populates="surgery")


class OTConsumable(Base):
    __tablename__ = "ot_consumables"

    id = Column(Integer, primary_key=True, index=True)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False)
    item_name = Column(String(300), nullable=False)
    item_code = Column(String(50))
    category = Column(String(100))  # suture, gloves, implant, drug
    quantity_used = Column(Float, nullable=False)
    unit = Column(String(50))
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    batch_number = Column(String(100))
    expiry_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    surgery = relationship("Surgery", back_populates="consumables")
