from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, JSON)
from sqlalchemy.sql import func
from app.core.database import Base


class FormTemplate(Base):
    """
    Dynamic clinical form definition (nursing assessment, ICU flowsheet, discharge
    checklist, specialty intake, etc). `schema_json` holds the field definitions,
    e.g. [{"key": "pain_score", "label": "Pain Score", "type": "number", "required": true}]
    so new form types don't require a DB migration.
    """
    __tablename__ = "form_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    department = Column(String(100))
    category = Column(String(100))          # assessment, checklist, intake, flowsheet
    version = Column(Integer, default=1)
    schema_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    source = Column(String(50))        # opd, ipd, emergency, ot, icu
    source_id = Column(Integer)

    data_json = Column(JSON, nullable=False)   # {field_key: value}
    submitted_by = Column(Integer, ForeignKey("users.id"))
    is_locked = Column(Boolean, default=False)  # locked once co-signed / finalized
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
