from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PatientCategory(str, enum.Enum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    MEDICAL_TOURISM = "medical_tourism"
    CORPORATE = "corporate"


class PatientCategoryProfile(Base):
    """
    Items 201-203 (International Patient / Medical Tourism / Corporate Healthcare)
    deliberately built as a one-to-one extension of `Patient` rather than new
    columns on the existing `patients` table or three separate modules — these
    are registration/billing *variants* of an ordinary patient, not distinct
    clinical domains, so they share one row shape differentiated by `category`.
    Keeping it a separate table avoids an alembic migration touching the
    existing `patients` table (lower risk on a live system).
    """
    __tablename__ = "patient_category_profiles"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True)
    category = Column(Enum(PatientCategory), default=PatientCategory.DOMESTIC)

    # International / medical tourism fields
    country_of_origin = Column(String(100), nullable=True)
    passport_number = Column(String(50), nullable=True)
    visa_number = Column(String(50), nullable=True)
    visa_expiry = Column(Date, nullable=True)
    preferred_language = Column(String(50), nullable=True)
    interpreter_required = Column(Boolean, default=False)
    facilitator_agency = Column(String(200), nullable=True)   # medical tourism facilitator, if any

    # Corporate healthcare fields
    corporate_employer_name = Column(String(200), nullable=True)
    corporate_employee_id = Column(String(100), nullable=True)
    corporate_scheme_name = Column(String(200), nullable=True)
    corporate_tpa_id = Column(Integer, ForeignKey("insurance_companies.id"), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
