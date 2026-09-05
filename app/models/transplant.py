from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class OrganType(str, enum.Enum):
    KIDNEY = "kidney"
    LIVER = "liver"
    HEART = "heart"
    LUNG = "lung"
    PANCREAS = "pancreas"
    CORNEA = "cornea"
    BONE_MARROW = "bone_marrow"


class DonorType(str, enum.Enum):
    LIVING_RELATED = "living_related"
    LIVING_UNRELATED = "living_unrelated"
    DECEASED = "deceased"


class WaitlistStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    TRANSPLANTED = "transplanted"
    REMOVED = "removed"
    DECEASED = "deceased"


class TransplantCandidate(Base):
    """A patient on the transplant waitlist for a specific organ. Kept
    separate from the eventual TransplantCase (below) since a candidate can
    be waitlisted for a long time before (or without ever) getting matched."""
    __tablename__ = "transplant_candidates"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    transplant_surgeon_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    organ_needed = Column(Enum(OrganType), nullable=False)
    blood_group = Column(String(5), nullable=True)
    listed_date = Column(Date, server_default=func.current_date())
    urgency_score = Column(Integer, nullable=True)     # hospital/registry-specific scoring
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.ACTIVE)

    workup_complete = Column(Boolean, default=False)
    hla_typing_done = Column(Boolean, default=False)
    ethics_committee_cleared = Column(Boolean, default=False)

    removed_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TransplantCase(Base):
    """The actual transplant event — created once a candidate is matched."""
    __tablename__ = "transplant_cases"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("transplant_candidates.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    transplant_surgeon_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)

    organ = Column(Enum(OrganType), nullable=False)
    donor_type = Column(Enum(DonorType), nullable=False)
    donor_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # if living donor is also a hospital patient
    donor_relation = Column(String(100), nullable=True)   # e.g. "sibling", "spouse"

    surgery_date = Column(Date, nullable=True)
    ot_surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=True)   # links to existing OT module

    cross_match_result = Column(String(50), nullable=True)   # negative/positive
    immunosuppression_protocol = Column(Text, nullable=True)
    outcome = Column(String(100), nullable=True)   # e.g. "successful", "graft_failure", "rejection_episode"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TransplantFollowUp(Base):
    """Post-transplant surveillance — rejection monitoring, immunosuppression titration."""
    __tablename__ = "transplant_follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("transplant_cases.id"), nullable=False)
    visit_date = Column(Date, server_default=func.current_date())
    days_post_transplant = Column(Integer, nullable=True)

    graft_function_status = Column(String(100), nullable=True)   # e.g. "stable", "declining"
    rejection_signs = Column(Boolean, default=False)
    immunosuppression_levels = Column(JSON, nullable=True)   # {"tacrolimus_level": 8.2, ...}
    medication_adjustment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
