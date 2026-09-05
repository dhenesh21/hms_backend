from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ProviderType(str, enum.Enum):
    INDIVIDUAL_PRACTITIONER = "individual_practitioner"
    FACILITY = "facility"
    LAB = "lab"
    PHARMACY = "pharmacy"


class ProviderRegistryEntry(Base):
    """
    National/network provider directory entry (item 238) — distinct from
    `DoctorProfile` (which is HR/scheduling data for staff who work here).
    This is the identity a provider is known by *outside* this hospital: a
    national registration number (India's NMR/HPR-style ID, an NPI in a US
    context, or whatever the local registry issues), used when this hospital
    needs to reference a provider in an external referral, claim, or
    interoperability message (HL7/FHIR Practitioner resource — see
    routers/fhir.py). A `DoctorProfile` optionally links to one of these via
    `registry_entry_id` when the doctor also has an external registration;
    the registry entry can also exist standalone for providers who refer
    patients here but don't work here.
    """
    __tablename__ = "provider_registry_entries"

    id = Column(Integer, primary_key=True, index=True)
    provider_type = Column(Enum(ProviderType), nullable=False)
    national_registry_id = Column(String(100), unique=True, nullable=True)   # external ID, e.g. HPR ID
    full_name = Column(String(300), nullable=False)
    specialization = Column(String(200), nullable=True)
    registration_council = Column(String(200), nullable=True)   # e.g. "Medical Council of India"
    registration_valid_until = Column(Date, nullable=True)

    linked_doctor_profile_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    is_internal = Column(Boolean, default=False)      # true if this provider works at this hospital
    is_verified = Column(Boolean, default=False)

    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
