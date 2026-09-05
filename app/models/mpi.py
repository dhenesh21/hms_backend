from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Float, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class MatchStatus(str, enum.Enum):
    POTENTIAL_DUPLICATE = "potential_duplicate"
    CONFIRMED_DUPLICATE = "confirmed_duplicate"
    NOT_A_MATCH = "not_a_match"
    MERGED = "merged"


class MPIMatchCandidate(Base):
    """
    Master Patient Index (item 237) — this system already has one Patient
    table with a unique UHID, so MPI here is specifically about catching
    duplicate registrations (same person registered twice — different UHID,
    typo'd name, remarried surname, etc), not about being a system of record
    across separate hospital databases (that's Health Information Exchange,
    item 257 — a genuinely different, external-integration problem, not
    built here). Deterministic + fuzzy matching runs as a background/manual
    process (see routers/mpi.py's `/scan` endpoint) and writes candidate
    pairs here for a human to confirm before any merge happens — this system
    NEVER auto-merges patient records, that's a clinical-safety decision that
    always needs a person to confirm.
    """
    __tablename__ = "mpi_match_candidates"

    id = Column(Integer, primary_key=True, index=True)
    patient_id_a = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient_id_b = Column(Integer, ForeignKey("patients.id"), nullable=False)

    match_score = Column(Float, nullable=False)          # 0-1, higher = more likely same person
    match_reasons = Column(JSON, default=list)            # ["same_dob_phone", "similar_name", ...]
    status = Column(Enum(MatchStatus), default=MatchStatus.POTENTIAL_DUPLICATE)

    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    merged_into_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    merged_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatientMergeLog(Base):
    """Audit trail of an actual merge — what survived, what got folded in,
    for anyone who needs to trace a record's history after a merge."""
    __tablename__ = "patient_merge_logs"

    id = Column(Integer, primary_key=True, index=True)
    match_candidate_id = Column(Integer, ForeignKey("mpi_match_candidates.id"), nullable=False)
    surviving_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    merged_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    merged_patient_old_uhid = Column(String(20), nullable=True)   # preserved for lookup after merge
    merged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    merge_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
