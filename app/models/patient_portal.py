from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PatientAccount(Base):
    """
    Login identity for the Patient Portal — deliberately separate from `users`
    (staff table) so a patient token can never satisfy a staff-only dependency
    and vice versa. One account per Patient (uhid), password-based for now.
    """
    __tablename__ = "patient_accounts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeedbackCategory(str, enum.Enum):
    DOCTOR = "doctor"
    NURSING = "nursing"
    FACILITY = "facility"
    BILLING = "billing"
    FOOD = "food"
    OVERALL = "overall"


class PatientFeedback(Base):
    __tablename__ = "patient_feedback"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    source = Column(String(50), nullable=True)          # opd, ipd
    source_id = Column(Integer, nullable=True)
    category = Column(Enum(FeedbackCategory), default=FeedbackCategory.OVERALL)
    rating = Column(Integer, nullable=False)             # 1-5
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GrievanceStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class PatientGrievance(Base):
    __tablename__ = "patient_grievances"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    subject = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    department_concerned = Column(String(100), nullable=True)
    status = Column(Enum(GrievanceStatus), default=GrievanceStatus.OPEN)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
