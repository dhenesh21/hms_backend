from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class InfectionSource(str, enum.Enum):
    HOSPITAL_ACQUIRED = "hospital_acquired"  # HAI / nosocomial
    COMMUNITY_ACQUIRED = "community_acquired"
    UNKNOWN = "unknown"


class InfectionStatus(str, enum.Enum):
    REPORTED = "reported"
    UNDER_INVESTIGATION = "under_investigation"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    RULED_OUT = "ruled_out"


class PrecautionType(str, enum.Enum):
    STANDARD = "standard"
    CONTACT = "contact"
    DROPLET = "droplet"
    AIRBORNE = "airborne"
    PROTECTIVE = "protective"  # reverse isolation, for immunocompromised patients


class InfectionIncident(Base):
    """
    Infection surveillance record - roadmap's "Infection Control" /
    "Infection Audit" / "Infection KPIs". Tracks suspected/confirmed
    infections, especially hospital-acquired ones, for audit and reporting.
    """
    __tablename__ = "infection_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(String(20), unique=True, index=True, nullable=False)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)

    infection_type = Column(String(200), nullable=False)  # e.g. "MRSA", "C. difficile", "UTI"
    source = Column(Enum(InfectionSource), default=InfectionSource.UNKNOWN)
    status = Column(Enum(InfectionStatus), default=InfectionStatus.REPORTED)

    date_identified = Column(DateTime(timezone=True), server_default=func.now())
    symptoms = Column(Text, nullable=True)
    lab_confirmation_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)

    corrective_action = Column(Text, nullable=True)
    resolved_date = Column(DateTime(timezone=True), nullable=True)

    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    isolation = relationship("IsolationPrecaution", back_populates="infection_incident", uselist=False)


class IsolationPrecaution(Base):
    """
    Active isolation precaution for a patient - links to a bed/ward so
    housekeeping and nursing both know a room needs special handling.
    """
    __tablename__ = "isolation_precautions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=True)
    infection_incident_id = Column(Integer, ForeignKey("infection_incidents.id"), nullable=True)

    precaution_type = Column(Enum(PrecautionType), default=PrecautionType.STANDARD)
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    started_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    infection_incident = relationship("InfectionIncident", back_populates="isolation")
