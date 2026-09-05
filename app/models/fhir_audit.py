from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class FHIRAccessLog(Base):
    """
    Audit trail of external FHIR API access — standard interoperability
    compliance practice (know who pulled what patient data out via the FHIR
    facade, and when). Deliberately lightweight — this logs the request, it
    doesn't gate it; access control is the existing RBAC (get_current_user +
    role checks) on each endpoint, same as everywhere else in this codebase.
    """
    __tablename__ = "fhir_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    accessed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)     # Patient, Observation, etc
    resource_id = Column(String(50), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
