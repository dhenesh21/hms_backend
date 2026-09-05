from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class SampleStatus(str, enum.Enum):
    ORDERED = "ordered"
    SAMPLE_COLLECTED = "sample_collected"
    SAMPLE_RECEIVED = "sample_received"
    PROCESSING = "processing"
    RESULT_ENTERED = "result_entered"
    APPROVED = "approved"
    REPORTED = "reported"
    REJECTED = "rejected"


class LabPriority(str, enum.Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"     # Immediate


class LabCategory(str, enum.Enum):
    HAEMATOLOGY = "haematology"
    BIOCHEMISTRY = "biochemistry"
    MICROBIOLOGY = "microbiology"
    IMMUNOLOGY = "immunology"
    HISTOPATHOLOGY = "histopathology"
    RADIOLOGY = "radiology"
    URINE = "urine"
    SEROLOGY = "serology"
    HORMONES = "hormones"
    OTHER = "other"


class LabTest(Base):
    """Master list of all available lab tests"""
    __tablename__ = "lab_tests"

    id = Column(Integer, primary_key=True, index=True)
    test_code = Column(String(20), unique=True, nullable=False, index=True)
    test_name = Column(String(300), nullable=False)
    category = Column(Enum(LabCategory), nullable=False)
    sample_type = Column(String(100))   # Blood, Urine, Stool, Swab
    normal_range = Column(String(200))
    unit = Column(String(50))
    methodology = Column(String(200))
    turnaround_time_hours = Column(Integer, default=24)
    price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    instructions = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("LabOrderItem", back_populates="test")


class LabOrder(Base):
    """A lab order can have multiple tests"""
    __tablename__ = "lab_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ordered_by = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    priority = Column(Enum(LabPriority), default=LabPriority.ROUTINE)

    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    clinical_info = Column(Text)
    ordered_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    patient = relationship("Patient")
    items = relationship("LabOrderItem", back_populates="order")


class LabOrderItem(Base):
    """Individual test within an order"""
    __tablename__ = "lab_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("lab_tests.id"), nullable=False)
    status = Column(Enum(SampleStatus), default=SampleStatus.ORDERED)

    # Sample info
    barcode = Column(String(50), unique=True, index=True)
    sample_collected_at = Column(DateTime(timezone=True))
    sample_collected_by = Column(Integer, ForeignKey("users.id"))
    sample_received_at = Column(DateTime(timezone=True))
    sample_received_by = Column(Integer, ForeignKey("users.id"))

    # Results
    result_value = Column(String(500))
    result_numeric = Column(Float)
    result_unit = Column(String(50))
    result_status = Column(String(20))  # normal, high, low, critical
    normal_range = Column(String(200))
    remarks = Column(Text)

    # Workflow
    result_entered_at = Column(DateTime(timezone=True))
    result_entered_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(Integer, ForeignKey("doctor_profiles.id"))

    reject_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("LabOrder", back_populates="items")
    test = relationship("LabTest", back_populates="order_items")
    sub_results = relationship("LabSubResult", back_populates="order_item")


class LabSubResult(Base):
    """For panel tests (e.g. CBC has WBC, RBC, Hb etc.)"""
    __tablename__ = "lab_sub_results"

    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("lab_order_items.id"), nullable=False)
    parameter_name = Column(String(200), nullable=False)
    result_value = Column(String(300))
    result_numeric = Column(Float)
    unit = Column(String(50))
    normal_range = Column(String(200))
    result_status = Column(String(20))  # normal, high, low, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("LabOrderItem", back_populates="sub_results")
