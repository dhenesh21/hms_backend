from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class VisitorStatus(str, enum.Enum):
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


class LostFoundStatus(str, enum.Enum):
    REPORTED = "reported"
    CLAIMED = "claimed"
    UNCLAIMED = "unclaimed"  # past retention period, disposed/donated


class LostFoundType(str, enum.Enum):
    LOST_BY_PATIENT = "lost_by_patient"   # patient/attendant lost something
    FOUND_ITEM = "found_item"             # staff found an item, no owner yet


class Visitor(Base):
    """
    Visitor check-in/out - roadmap's "Visitor / Attendant Management".
    Links to the patient being visited (usually via their active IPD
    admission) so security/nursing can see who's visiting whom.
    """
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    pass_number = Column(String(20), unique=True, index=True, nullable=False)

    visitor_name = Column(String(200), nullable=False)
    visitor_phone = Column(String(20), nullable=True)
    id_proof_type = Column(String(50), nullable=True)  # e.g. "Aadhaar", "Driving License"
    id_proof_number = Column(String(50), nullable=True)
    relation_to_patient = Column(String(100), nullable=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    status = Column(Enum(VisitorStatus), default=VisitorStatus.CHECKED_IN)
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    check_out_time = Column(DateTime(timezone=True), nullable=True)

    issued_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LostFoundItem(Base):
    """Lost & Found register - roadmap's "Lost & Found"."""
    __tablename__ = "lost_found_items"

    id = Column(Integer, primary_key=True, index=True)
    item_number = Column(String(20), unique=True, index=True, nullable=False)

    entry_type = Column(Enum(LostFoundType), default=LostFoundType.FOUND_ITEM)
    item_description = Column(Text, nullable=False)
    location_found_lost = Column(String(200), nullable=True)  # e.g. "Ward 3B", "OPD waiting area"

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # if linked to a specific patient
    reporter_name = Column(String(200), nullable=True)
    reporter_phone = Column(String(20), nullable=True)

    status = Column(Enum(LostFoundStatus), default=LostFoundStatus.REPORTED)
    date_reported = Column(DateTime(timezone=True), server_default=func.now())

    claimed_by = Column(String(200), nullable=True)
    claimed_date = Column(DateTime(timezone=True), nullable=True)
    claim_verification = Column(Text, nullable=True)  # notes on how ownership was verified

    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
