from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import difflib

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mpi import MPIMatchCandidate, PatientMergeLog, MatchStatus
from app.models.patient import Patient
from app.models.user import User
from app.schemas.mpi import (
    MPIScanResult, MPICandidateResponse, MPIReviewRequest, MergeRequest, MergeLogResponse,
)

router = APIRouter(prefix="/mpi", tags=["Master Patient Index"])


def _name_similarity(a: Patient, b: Patient) -> float:
    """Stdlib-only fuzzy name match (difflib.SequenceMatcher) — no fuzzy-matching
    library install available in this environment; this is a reasonable
    dependency-free baseline, not a claim of best-in-class matching. Swap for
    rapidfuzz/jellyfish if available in your deployment for better results."""
    name_a = f"{a.first_name} {a.last_name}".lower().strip()
    name_b = f"{b.first_name} {b.last_name}".lower().strip()
    return difflib.SequenceMatcher(None, name_a, name_b).ratio()


@router.post("/scan", response_model=MPIScanResult)
async def scan_for_duplicates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Deterministic + fuzzy scan for potential duplicate patient registrations.
    NEVER auto-merges — every candidate found here needs a human review via
    POST /mpi/candidates/{id}/review before anything happens to the records.
    O(n^2) over all patients — fine for a manual/periodic admin-triggered
    scan on a few thousand patients, not something to run on every
    registration; wiring this to a scheduler is Group 6 infra scope.
    """
    patients = db.query(Patient).all()
    existing_pairs = set()
    for m in db.query(MPIMatchCandidate).all():
        existing_pairs.add((min(m.patient_id_a, m.patient_id_b), max(m.patient_id_a, m.patient_id_b)))

    found = 0
    for i in range(len(patients)):
        for j in range(i + 1, len(patients)):
            a, b = patients[i], patients[j]
            pair_key = (min(a.id, b.id), max(a.id, b.id))
            if pair_key in existing_pairs:
                continue

            reasons = []
            score = 0.0
            if a.date_of_birth == b.date_of_birth:
                score += 0.4
                reasons.append("same_date_of_birth")
            if a.phone and a.phone == b.phone:
                score += 0.3
                reasons.append("same_phone")
            name_sim = _name_similarity(a, b)
            if name_sim > 0.85:
                score += 0.3
                reasons.append("similar_name")
            elif name_sim > 0.6:
                score += 0.15
                reasons.append("somewhat_similar_name")

            if score >= 0.5:
                db.add(MPIMatchCandidate(
                    patient_id_a=a.id, patient_id_b=b.id,
                    match_score=round(min(score, 1.0), 2), match_reasons=reasons,
                ))
                found += 1

    db.commit()
    return MPIScanResult(candidates_found=found)


@router.get("/candidates", response_model=List[MPICandidateResponse])
async def list_candidates(status: MatchStatus = MatchStatus.POTENTIAL_DUPLICATE, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return db.query(MPIMatchCandidate).filter(
        MPIMatchCandidate.status == status
    ).order_by(MPIMatchCandidate.match_score.desc()).all()


@router.post("/candidates/{candidate_id}/review", response_model=MPICandidateResponse)
async def review_candidate(candidate_id: int, data: MPIReviewRequest, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    candidate = db.query(MPIMatchCandidate).filter(MPIMatchCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Match candidate not found")
    candidate.status = data.status
    candidate.review_notes = data.review_notes
    candidate.reviewed_by = current_user.id
    candidate.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/merge", response_model=MergeLogResponse)
async def merge_patients(candidate_id: int, data: MergeRequest, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """
    Records the merge decision and audit trail. Does NOT reassign every
    foreign key across ~150 tables that reference patient_id — that's a
    genuinely large, risky data-migration operation specific to whichever
    tables actually have data for the merged patient, not something to do
    generically and silently in one endpoint. This logs the decision
    (which patient survives, which is merged away, preserving the old UHID
    for lookup) so the actual FK-reassignment migration can be run
    deliberately, reviewed, and rolled back if needed — a merge is
    higher-risk than almost anything else in this system and deserves that
    caution rather than a single irreversible click.
    """
    candidate = db.query(MPIMatchCandidate).filter(MPIMatchCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Match candidate not found")
    if candidate.status != MatchStatus.CONFIRMED_DUPLICATE:
        raise HTTPException(status_code=400, detail="Candidate must be marked confirmed_duplicate before merging")
    if data.surviving_patient_id not in (candidate.patient_id_a, candidate.patient_id_b):
        raise HTTPException(status_code=400, detail="surviving_patient_id must be one of the two matched patients")

    merged_id = candidate.patient_id_b if data.surviving_patient_id == candidate.patient_id_a else candidate.patient_id_a
    merged_patient = db.query(Patient).filter(Patient.id == merged_id).first()

    log = PatientMergeLog(
        match_candidate_id=candidate.id, surviving_patient_id=data.surviving_patient_id,
        merged_patient_id=merged_id, merged_patient_old_uhid=merged_patient.uhid if merged_patient else None,
        merged_by=current_user.id, merge_notes=data.merge_notes,
    )
    db.add(log)
    candidate.status = MatchStatus.MERGED
    candidate.merged_into_patient_id = data.surviving_patient_id
    candidate.merged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log)
    return log
