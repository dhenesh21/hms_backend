from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum, Float
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class FacilityType(str, enum.Enum):
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    LAB = "lab"
    PHARMACY = "pharmacy"
    DIAGNOSTIC_CENTER = "diagnostic_center"
    BLOOD_BANK = "blood_bank"


class FacilityRegistryEntry(Base):
    """
    Item 239 — directory of *other* facilities this hospital exchanges
    patients/referrals/results with (referring clinics, partner labs, blood
    banks), plus this hospital's own entry for when it needs to identify
    itself in an outbound HL7/FHIR message. This is intentionally separate
    from Group 2's own internal Facility Management (housekeeping/maintenance
    of this hospital's physical spaces) — that's about managing this
    building; this is an address book of external institutions.
    """
    __tablename__ = "facility_registry_entries"

    id = Column(Integer, primary_key=True, index=True)
    facility_type = Column(Enum(FacilityType), nullable=False)
    name = Column(String(300), nullable=False)
    national_facility_id = Column(String(100), unique=True, nullable=True)  # external registry ID, e.g. HFR ID
    is_self = Column(Boolean, default=False)    # true for this hospital's own entry

    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
