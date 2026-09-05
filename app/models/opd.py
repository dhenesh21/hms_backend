from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    JSON,
    Date,
    Enum,
    Boolean
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class VisitStatus(str, enum.Enum):
    WAITING = "waiting"
    IN_CONSULTATION = "in_consultation"
    COMPLETED = "completed"
    REFERRED = "referred"


class OPDVisit(Base):
    __tablename__ = "opd_visits"

    id = Column(Integer, primary_key=True, index=True)

    visit_number = Column(
        String(20),
        unique=True,
        index=True,
        nullable=False
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctor_profiles.id"),
        nullable=False
    )

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=True
    )

    visit_date = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    status = Column(
        Enum(VisitStatus),
        default=VisitStatus.WAITING
    )

    temperature = Column(Float)

    blood_pressure_systolic = Column(Integer)

    blood_pressure_diastolic = Column(Integer)

    pulse_rate = Column(Integer)

    respiratory_rate = Column(Integer)

    oxygen_saturation = Column(Float)

    height_cm = Column(Float)

    weight_kg = Column(Float)

    bmi = Column(Float)

    chief_complaint = Column(Text)

    history_of_present_illness = Column(Text)

    past_medical_history = Column(Text)

    physical_examination = Column(Text)

    clinical_notes = Column(Text)

    primary_diagnosis = Column(Text)

    secondary_diagnosis = Column(Text)

    icd_codes = Column(JSON, default=list)

    treatment_plan = Column(Text)

    advice = Column(Text)

    diet_advice = Column(Text)

    activity_advice = Column(Text)

    follow_up_required = Column(Boolean, default=False)

    follow_up_date = Column(Date)

    follow_up_notes = Column(Text)

    referred_to = Column(String(200))

    referral_notes = Column(Text)

    created_by = Column(
        Integer,
        ForeignKey("users.id")
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    patient = relationship(
        "Patient",
        back_populates="opd_visits"
    )

    doctor = relationship(
        "DoctorProfile",
        back_populates="opd_visits"
    )

    appointment = relationship(
        "Appointment",
        back_populates="opd_visit"
    )

    prescriptions = relationship(
        "Prescription",
        back_populates="opd_visit"
    )


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    opd_visit_id = Column(
        Integer,
        ForeignKey("opd_visits.id"),
        nullable=False
    )

    drug_name = Column(String(200), nullable=False)

    generic_name = Column(String(200))

    dosage = Column(String(100))

    frequency = Column(String(100))

    duration_days = Column(Integer)

    route = Column(String(50))

    instructions = Column(Text)

    quantity = Column(Integer)

    is_dispensed = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    opd_visit = relationship(
        "OPDVisit",
        back_populates="prescriptions"
    )


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True, index=True)

    admission_number = Column(
        String(20),
        unique=True,
        nullable=False
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    admitting_doctor_id = Column(
        Integer,
        ForeignKey("doctor_profiles.id")
    )

    admission_date = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    discharge_date = Column(DateTime(timezone=True))

    admission_type = Column(String(50))

    ward = Column(String(100))

    bed_number = Column(String(20))

    diagnosis_at_admission = Column(Text)

    discharge_summary = Column(Text)

    status = Column(String(20), default="admitted")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    patient = relationship(
        "Patient",
        back_populates="admissions"
    )


class OpdAuditLog(Base):
    __tablename__ = "opd_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    action = Column(
        String(100),
        nullable=False
    )

    resource = Column(String(100))

    resource_id = Column(Integer)

    details = Column(JSON)

    ip_address = Column(String(45))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    user = relationship(
        "User",
        back_populates="opd_audit_logs"
    )