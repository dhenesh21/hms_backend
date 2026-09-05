from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DataCategory(str, enum.Enum):
    DEMOGRAPHICS = "demographics"
    DIAGNOSES = "diagnoses"
    MEDICATIONS = "medications"
    LAB_RESULTS = "lab_results"
    IMAGING = "imaging"
    ALLERGIES = "allergies"
    FULL_RECORD = "full_record"


class ExchangeAuthStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DataExchangeAuthorization(Base):
    """
    Item 258 — patient consent scoped specifically to sharing data with an
    external party (a referring facility, an insurer, a partner lab —
    referenced via Group 5's own FacilityRegistryEntry/ProviderRegistryEntry
    rather than free text), as opposed to Group 4's `PatientConsent` which
    covers internal clinical consents (surgery, anesthesia, research). Kept
    as a separate table rather than overloading `PatientConsent` because the
    two have genuinely different shapes: this one needs an external-party
    reference, a data-category scope, and an expiry — none of which apply to
    "consent to this operation."

    This authorization is a *record of permission*, not an enforcement
    engine — the FHIR/HL7 endpoints in this same batch do not currently
    check against this table before returning data (that would need every
    external caller to be identified as acting on behalf of a specific
    registered party, which isn't set up yet — today's FHIR/HL7 access is
    gated by ordinary staff RBAC, same as everywhere else). Wiring FHIR/HL7
    access to check this table is the natural next step once external
    callers are actually authenticated as specific external parties rather
    than internal staff users.
    """
    __tablename__ = "data_exchange_authorizations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    authorized_facility_id = Column(Integer, ForeignKey("facility_registry_entries.id"), nullable=True)
    authorized_provider_id = Column(Integer, ForeignKey("provider_registry_entries.id"), nullable=True)
    authorized_party_name_freetext = Column(String(300), nullable=True)   # fallback if not yet in either registry

    data_categories = Column(JSON, default=list)     # list of DataCategory values
    purpose = Column(Text, nullable=True)
    status = Column(Enum(ExchangeAuthStatus), default=ExchangeAuthStatus.ACTIVE)

    consented_by_name = Column(String(200), nullable=True)
    signature_data = Column(Text, nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataExchangeLog(Base):
    """Every actual data pull/push that happened under an authorization —
    the audit trail a patient (or a regulator) could ask for: 'who has
    accessed my data and when, under what permission'."""
    __tablename__ = "data_exchange_logs"

    id = Column(Integer, primary_key=True, index=True)
    authorization_id = Column(Integer, ForeignKey("data_exchange_authorizations.id"), nullable=False)
    accessed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # internal staff who released it
    data_category = Column(Enum(DataCategory), nullable=False)
    record_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
