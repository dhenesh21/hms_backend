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


class DeathSource(str, enum.Enum):
    IPD = "ipd"
    EMERGENCY = "emergency"
    BROUGHT_DEAD = "brought_dead"
    OTHER = "other"


class BodyStatus(str, enum.Enum):
    IN_STORAGE = "in_storage"
    IN_POSTMORTEM = "in_postmortem"
    RELEASED = "released"


class MortuaryRecord(Base):
    """
    One record per death - roadmap's "Death Register". Links to whichever
    department the death occurred in (IPD admission or ER visit), tracks
    cold storage, postmortem, and release to the family/authorities.
    """
    __tablename__ = "mortuary_records"

    id = Column(Integer, primary_key=True, index=True)
    mortuary_number = Column(String(20), unique=True, index=True, nullable=False)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    death_source = Column(Enum(DeathSource), default=DeathSource.IPD)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    er_visit_id = Column(Integer, ForeignKey("er_visits.id"), nullable=True)

    date_of_death = Column(DateTime(timezone=True), server_default=func.now())
    cause_of_death = Column(Text, nullable=True)
    certified_by = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    is_mlc = Column(Boolean, default=False)  # medico-legal case, may require police/postmortem

    body_status = Column(Enum(BodyStatus), default=BodyStatus.IN_STORAGE)
    storage_unit = Column(String(50), nullable=True)  # e.g. "Freezer 3"
    stored_at = Column(DateTime(timezone=True), server_default=func.now())

    postmortem_required = Column(Boolean, default=False)
    postmortem_done = Column(Boolean, default=False)
    postmortem_date = Column(DateTime(timezone=True), nullable=True)
    postmortem_doctor = Column(String(200), nullable=True)
    postmortem_findings = Column(Text, nullable=True)

    released_to = Column(String(200), nullable=True)  # name of relative/authority
    released_relation = Column(String(100), nullable=True)
    release_date = Column(DateTime(timezone=True), nullable=True)
    death_certificate_number = Column(String(50), nullable=True)
    death_certificate_issued = Column(Boolean, default=False)

    notes = Column(Text, nullable=True)
    registered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
