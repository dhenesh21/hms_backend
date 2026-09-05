from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ScanType(str, enum.Enum):
    XRAY = "xray"
    CT = "ct"
    MRI = "mri"
    ULTRASOUND = "ultrasound"
    MAMMOGRAM = "mammogram"
    PET_SCAN = "pet_scan"
    DEXA = "dexa"
    FLUOROSCOPY = "fluoroscopy"
    ECHO = "echo"
    ECG = "ecg"


class ScanStatus(str, enum.Enum):
    ORDERED = "ordered"
    SCHEDULED = "scheduled"
    PATIENT_ARRIVED = "patient_arrived"
    IN_PROGRESS = "in_progress"
    IMAGES_UPLOADED = "images_uploaded"
    REPORT_PENDING = "report_pending"
    REPORTED = "reported"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class RadiologyOrder(Base):
    __tablename__ = "radiology_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ordered_by = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    radiologist_id = Column(Integer, ForeignKey("doctor_profiles.id"))
    # Technologist who actually operated the equipment and performed the
    # scan - a real RIS distinguishes this from the radiologist who later
    # reports on the images; previously there was no way to record who
    # ran the study at all.
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Which physical machine performed the study - links to the
    # Facility & Equipment module's equipment register (e.g. "CT-2",
    # "MRI-1"), so equipment utilization/maintenance history can be
    # cross-referenced against studies performed on it.
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)

    scan_type = Column(Enum(ScanType), nullable=False)
    body_part = Column(String(200), nullable=False)
    clinical_indication = Column(Text)
    contrast_required = Column(Boolean, default=False)
    priority = Column(String(20), default="routine")  # routine, urgent, stat
    status = Column(Enum(ScanStatus), default=ScanStatus.ORDERED)

    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    scheduled_date = Column(Date)
    scheduled_time = Column(String(10))
    performed_at = Column(DateTime(timezone=True))

    # Reporting
    findings = Column(Text)
    impression = Column(Text)
    recommendations = Column(Text)
    reported_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))

    # Which standardized template (if any) was used as the starting
    # point for this report - roadmap's Diagnostic Reporting item.
    # Nullable because a radiologist can always still write a report
    # from scratch without a template.
    report_template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=True)

    # Critical finding escalation - roadmap's real RIS requirement that
    # a radiologist can flag a result as needing urgent attention from
    # the ordering doctor, and that flag is trackable/queryable (not
    # just mentioned in free-text impression, which nobody can query on).
    is_critical_finding = Column(Boolean, default=False)
    critical_finding_notes = Column(Text, nullable=True)
    critical_finding_flagged_at = Column(DateTime(timezone=True), nullable=True)
    critical_finding_acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # PACS info
    pacs_study_id = Column(String(200))
    dicom_url = Column(String(500))

    price = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient")
    images = relationship("RadiologyImage", back_populates="order")


class RadiologyImage(Base):
    __tablename__ = "radiology_images"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_kb = Column(Integer)
    mime_type = Column(String(100))
    view_type = Column(String(100))  # AP, Lateral, Oblique
    dicom_file = Column(Boolean, default=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("RadiologyOrder", back_populates="images")
