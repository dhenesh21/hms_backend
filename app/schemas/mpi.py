from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.mpi import MatchStatus


class MPIScanResult(BaseModel):
    candidates_found: int


class MPICandidateResponse(BaseModel):
    id: int
    patient_id_a: int
    patient_id_b: int
    match_score: float
    match_reasons: Any
    status: MatchStatus
    created_at: datetime

    class Config:
        from_attributes = True


class MPIReviewRequest(BaseModel):
    status: MatchStatus
    review_notes: Optional[str] = None


class MergeRequest(BaseModel):
    surviving_patient_id: int
    merge_notes: Optional[str] = None


class MergeLogResponse(BaseModel):
    id: int
    match_candidate_id: int
    surviving_patient_id: int
    merged_patient_id: int
    merged_patient_old_uhid: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
