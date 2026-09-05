from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class MedicalRecordAccessLog(Base):
    """
    Item 291 — every view of a patient's clinical record, logged. This is
    distinct from Group 5's `FHIRAccessLog` (external/interoperability
    access only) and from `AuditLog` (system-wide admin actions like role
    changes) — this one is specifically "who looked at this patient's
    medical record and when," the audit trail a patient or a regulator
    would actually ask for.

    Honest scope note: this table and the `log_record_access()` helper
    below are called explicitly by `GET /medical-record-privacy/log-access`
    - they are NOT automatically wired into every existing clinical read
    endpoint across EMR/Lab/Radiology/etc (that's a genuinely large
    refactor touching dozens of already-built routers, not something to
    silently claim done). Wiring it as a FastAPI dependency injected into
    those routers is the natural next step; what exists now is the
    logging mechanism and the query/reporting side.
    """
    __tablename__ = "medical_record_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    accessed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource_type = Column(String(100), nullable=False)   # "emr", "lab_result", "clinical_document", etc
    resource_id = Column(String(50), nullable=True)
    access_reason = Column(String(200), nullable=True)     # e.g. "treatment", "billing_query"
    was_restricted_record = Column(Boolean, default=False)  # true if patient had an active PatientPrivacyFlag
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatientPrivacyFlag(Base):
    """
    Item 289 (Privacy Management) — marks a patient's record as needing
    elevated handling (VIP, staff member, high-profile, domestic-violence
    safety concern, etc). This flag doesn't itself change what any
    endpoint returns (that enforcement would need to be added per-endpoint,
    same honest-scope note as above) - what it does today is make the flag
    queryable so the UI can show a warning banner, and gives
    MedicalRecordAccessLog something to record against
    (`was_restricted_record`).
    """
    __tablename__ = "patient_privacy_flags"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True)
    reason = Column(Text, nullable=False)
    flagged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
