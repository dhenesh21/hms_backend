from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum, ForeignKey
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CodeSystem(str, enum.Enum):
    ICD10 = "icd10"
    ICD11 = "icd11"
    SNOMED_CT = "snomed_ct"
    LOINC = "loinc"
    RXNORM = "rxnorm"
    CPT = "cpt"
    LOCAL = "local"     # hospital's own internal codes, e.g. for a custom order catalog


class TerminologyCode(Base):
    """
    Item 240 — a local cache/reference table of standard clinical codes
    (ICD-10 diagnoses, LOINC lab codes, SNOMED-CT findings, etc), NOT a live
    connection to an external terminology server. Loading the full official
    code sets (ICD-10 alone is ~70,000 codes) needs a licensed data file from
    each code system's maintainer (WHO for ICD, Regenstrief for LOINC,
    SNOMED International for SNOMED-CT) — that's a data-licensing step this
    session can't perform, not a code gap. What's built is the *shape*:
    the table, search endpoint, and the hook points (DiagnosisRecord.icd_code,
    LabTest, etc already store free-text codes elsewhere in this codebase) —
    load real code data into this table via CSV import once you have a
    licensed source, and every module that stores a bare code string can
    start validating/looking up against it.
    """
    __tablename__ = "terminology_codes"

    id = Column(Integer, primary_key=True, index=True)
    code_system = Column(Enum(CodeSystem), nullable=False)
    code = Column(String(50), nullable=False)
    display_name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    parent_code = Column(String(50), nullable=True)     # for hierarchical systems (ICD chapter/category)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TerminologyMapping(Base):
    """Cross-mapping between code systems (e.g. a local order code -> LOINC),
    so this hospital's own catalog can still speak a standard code externally."""
    __tablename__ = "terminology_mappings"

    id = Column(Integer, primary_key=True, index=True)
    source_code_id = Column(Integer, ForeignKey("terminology_codes.id"), nullable=False)
    target_code_id = Column(Integer, ForeignKey("terminology_codes.id"), nullable=False)
    mapping_confidence = Column(String(20), nullable=True)   # exact, broader, narrower, approximate
    created_at = Column(DateTime(timezone=True), server_default=func.now())
