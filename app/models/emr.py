from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DocumentType(str, enum.Enum):
    LAB_REPORT = "lab_report"
    SCAN_REPORT = "scan_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    REFERRAL_LETTER = "referral_letter"
    PRESCRIPTION = "prescription"
    CONSENT_FORM = "consent_form"
    OPERATION_NOTES = "operation_notes"
    OTHER = "other"


class AllergyType(str, enum.Enum):
    DRUG = "drug"
    FOOD = "food"
    ENVIRONMENT = "environment"
    OTHER = "other"


class AllergySeverity(str, enum.Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life_threatening"


class PatientAllergy(Base):
    __tablename__ = "patient_allergies"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    allergen = Column(String(200), nullable=False)
    allergy_type = Column(Enum(AllergyType), default=AllergyType.DRUG)
    severity = Column(Enum(AllergySeverity), default=AllergySeverity.MILD)
    reaction = Column(Text)
    is_active = Column(Boolean, default=True)
    reported_date = Column(Date)
    reported_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChronicCondition(Base):
    __tablename__ = "chronic_conditions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    condition_name = Column(String(200), nullable=False)
    icd_code = Column(String(20))
    diagnosed_date = Column(Date)
    diagnosed_by = Column(String(200))
    current_status = Column(String(100))  # active, controlled, resolved
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MedicationHistory(Base):
    __tablename__ = "medication_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    drug_name = Column(String(200), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    prescribed_by = Column(String(200))
    reason = Column(Text)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FamilyHistory(Base):
    __tablename__ = "family_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    relation = Column(String(100), nullable=False)
    condition = Column(String(200), nullable=False)
    age_of_onset = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SurgicalHistory(Base):
    __tablename__ = "surgical_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    procedure_name = Column(String(300), nullable=False)
    surgery_date = Column(Date)
    surgeon = Column(String(200))
    hospital = Column(String(200))
    complications = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImmunizationRecord(Base):
    __tablename__ = "immunization_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    vaccine_name = Column(String(200), nullable=False)
    dose_number = Column(Integer, default=1)
    administered_date = Column(Date, nullable=False)
    administered_by = Column(String(200))
    batch_number = Column(String(100))
    next_due_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClinicalDocument(Base):
    __tablename__ = "clinical_documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    file_path = Column(String(500))
    file_name = Column(String(300))
    file_size_kb = Column(Integer)
    mime_type = Column(String(100))
    source = Column(String(200))           # Lab name, Hospital name
    document_date = Column(Date)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"))
    diagnosis = Column(Text, nullable=False)
    icd_code = Column(String(20))
    diagnosis_type = Column(String(50), default="primary")  # primary, secondary, differential
    diagnosis_date = Column(Date, server_default=func.current_date())
    source = Column(String(50), default="opd")   # opd, ipd, emergency
    source_id = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
