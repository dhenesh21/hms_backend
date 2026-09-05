from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class MedicalCodingCodeSystem(str, enum.Enum):
    ICD10 = "icd10"
    CPT = "cpt"


class CodeType(str, enum.Enum):
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"


class MedicalCode(Base):
    __tablename__ = "medical_codes"

    id = Column(Integer, primary_key=True, index=True)
    code_system = Column(Enum(MedicalCodingCodeSystem), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)


class PatientCoding(Base):
    __tablename__ = "patient_coding"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    code_id = Column(Integer, ForeignKey("medical_codes.id"), nullable=False)
    code_type = Column(Enum(CodeType), nullable=False)

    notes = Column(Text, nullable=True)
    coded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    coded_at = Column(DateTime(timezone=True), server_default=func.now())
