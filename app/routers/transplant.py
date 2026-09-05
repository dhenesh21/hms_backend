from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.transplant import TransplantCandidate, TransplantCase, TransplantFollowUp, WaitlistStatus
from app.models.user import User
from app.schemas.transplant import (
    CandidateCreate, CandidateUpdate, CandidateResponse,
    TransplantCaseCreate, TransplantCaseUpdate, TransplantCaseResponse,
    FollowUpCreate, FollowUpResponse,
)

router = APIRouter(prefix="/transplant", tags=["Transplant"])


@router.post("/candidates", response_model=CandidateResponse, status_code=201)
async def add_candidate(data: CandidateCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    candidate = TransplantCandidate(**data.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/candidates", response_model=List[CandidateResponse])
async def list_candidates(organ_needed: Optional[str] = None, status: Optional[WaitlistStatus] = None,
                           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(TransplantCandidate)
    if organ_needed:
        q = q.filter(TransplantCandidate.organ_needed == organ_needed)
    if status:
        q = q.filter(TransplantCandidate.status == status)
    else:
        q = q.filter(TransplantCandidate.status == WaitlistStatus.ACTIVE)
    return q.order_by(TransplantCandidate.urgency_score.desc()).all()


@router.patch("/candidates/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(candidate_id: int, data: CandidateUpdate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    candidate = db.query(TransplantCandidate).filter(TransplantCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(candidate, k, v)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/cases", response_model=TransplantCaseResponse, status_code=201)
async def create_case(data: TransplantCaseCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    candidate = db.query(TransplantCandidate).filter(TransplantCandidate.id == data.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    case = TransplantCase(**data.model_dump())
    db.add(case)
    candidate.status = WaitlistStatus.TRANSPLANTED
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases", response_model=List[TransplantCaseResponse])
async def list_cases(patient_id: Optional[int] = None, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    q = db.query(TransplantCase)
    if patient_id:
        q = q.filter(TransplantCase.patient_id == patient_id)
    return q.all()


@router.patch("/cases/{case_id}", response_model=TransplantCaseResponse)
async def update_case(case_id: int, data: TransplantCaseUpdate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    case = db.query(TransplantCase).filter(TransplantCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    db.commit()
    db.refresh(case)
    return case


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=201)
async def add_follow_up(data: FollowUpCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    follow_up = TransplantFollowUp(**data.model_dump())
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.get("/follow-ups/case/{case_id}", response_model=List[FollowUpResponse])
async def list_follow_ups(case_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return db.query(TransplantFollowUp).filter(
        TransplantFollowUp.case_id == case_id
    ).order_by(TransplantFollowUp.visit_date.desc()).all()
