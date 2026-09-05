from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ConsentStatus(str, enum.Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REFUSED = "refused"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ConsentTemplate(Base):
    """Master consent-form templates (surgery, anesthesia, HIV test, research, data-sharing, etc.)."""
    __tablename__ = "consent_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))          # procedure, anesthesia, research, data_sharing, general
    body_text = Column(Text, nullable=False)
    requires_witness = Column(Boolean, default=False)
    validity_days = Column(Integer, nullable=True)   # null = no expiry
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatientConsent(Base):
    """A signed/pending instance of a consent for a specific patient + episode of care."""
    __tablename__ = "patient_consents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("consent_templates.id"), nullable=False)

    source = Column(String(50))          # opd, ipd, ot, emergency, research
    source_id = Column(Integer)

    status = Column(Enum(ConsentStatus), default=ConsentStatus.PENDING)
    consented_by_name = Column(String(200))       # patient, or guardian/next-of-kin
    relationship_to_patient = Column(String(100), default="self")
    signature_data = Column(Text, nullable=True)  # base64 signature / e-sign token
    witness_name = Column(String(200), nullable=True)
    explained_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # doctor who took consent

    signed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)

    metadata_json = Column(JSON, nullable=True)   # snapshot of filled-in fields, if template is dynamic
    created_at = Column(DateTime(timezone=True), server_default=func.now())
