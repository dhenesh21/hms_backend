from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class RelationType(str, enum.Enum):
    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    SIBLING = "sibling"
    GUARDIAN = "guardian"
    CAREGIVER = "caregiver"
    OTHER = "other"


class FamilyMember(Base):
    """
    Links a patient to family/proxy/caregivers (item 20). `linked_patient_id` is
    set when the family member is themselves a registered patient (enables the
    Family Health view, item 196, without duplicating their demographic data);
    it's left null for a caregiver who isn't a hospital patient — their basic
    contact details are then held directly on this row.
    """
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    linked_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)

    name = Column(String(200), nullable=True)          # only used when not linked_patient_id
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    relation_type = Column(Enum(RelationType), nullable=False)
    is_emergency_contact = Column(Boolean, default=False)
    is_authorized_proxy = Column(Boolean, default=False)   # can consent/decide on patient's behalf
    proxy_scope_notes = Column(Text, nullable=True)         # e.g. "minor's guardian", "POA for medical decisions"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
