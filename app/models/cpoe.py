from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class OrderType(str, enum.Enum):
    LAB = "lab"
    RADIOLOGY = "radiology"
    MEDICATION = "medication"
    NURSING = "nursing"
    PROCEDURE = "procedure"
    DIET = "diet"
    CONSULTATION = "consultation"
    BLOOD_BANK = "blood_bank"
    OTHER = "other"


class OrderPriority(str, enum.Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class OrderSet(Base):
    """A reusable bundle of orders (e.g. 'Post-Op Day 1', 'Sepsis Protocol')."""
    __tablename__ = "order_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    department = Column(String(100))
    description = Column(Text)
    specialty = Column(String(100))
    items = Column(JSON, default=list)   # [{order_type, item_name, instructions, default_priority}]
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClinicalOrder(Base):
    """Single CPOE order — the core unit routed to Lab/Radiology/Pharmacy/Nursing queues."""
    __tablename__ = "clinical_orders"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ordering_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    order_type = Column(Enum(OrderType), nullable=False)
    order_set_id = Column(Integer, ForeignKey("order_sets.id"), nullable=True)

    item_name = Column(String(300), nullable=False)   # test name / drug name / procedure name
    instructions = Column(Text)
    priority = Column(Enum(OrderPriority), default=OrderPriority.ROUTINE)
    status = Column(Enum(OrderStatus), default=OrderStatus.ORDERED)

    # context — links order to the visit it was raised in
    source = Column(String(50))          # opd, ipd, emergency, ot
    source_id = Column(Integer)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    # downstream fulfilment linkage (populated once routed/actioned by the target module)
    fulfilled_module = Column(String(50))     # e.g. "lab_order", "prescription"
    fulfilled_ref_id = Column(Integer)

    # safety-check results captured at order time (drug interaction / allergy screen)
    safety_check_result = Column(JSON, nullable=True)

    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ClinicalOrderNote(Base):
    """Free-text status trail on an order (nurse/pharmacist/tech notes)."""
    __tablename__ = "clinical_order_notes"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("clinical_orders.id"), nullable=False)
    note = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
