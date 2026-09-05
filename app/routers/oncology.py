from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.oncology import OncologyCase, ChemoCycle, OncologyFollowUp
from app.models.user import User
from app.schemas.oncology import (
    OncologyCaseCreate, OncologyCaseUpdate, OncologyCaseResponse,
    ChemoCycleCreate, ChemoCycleUpdate, ChemoCycleResponse,
    FollowUpCreate, FollowUpResponse,
)

router = APIRouter(prefix="/oncology", tags=["Oncology"])


@router.post("/cases", response_model=OncologyCaseResponse, status_code=201)
async def create_case(data: OncologyCaseCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    case = OncologyCase(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases", response_model=List[OncologyCaseResponse])
async def list_cases(patient_id: Optional[int] = None, active_only: bool = True,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(OncologyCase)
    if patient_id:
        q = q.filter(OncologyCase.patient_id == patient_id)
    if active_only:
        q = q.filter(OncologyCase.is_active == True)
    return q.all()


@router.patch("/cases/{case_id}", response_model=OncologyCaseResponse)
async def update_case(case_id: int, data: OncologyCaseUpdate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    case = db.query(OncologyCase).filter(OncologyCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    db.commit()
    db.refresh(case)
    return case


@router.post("/chemo-cycles", response_model=ChemoCycleResponse, status_code=201)
async def schedule_cycle(data: ChemoCycleCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    cycle = ChemoCycle(**data.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/chemo-cycles/case/{case_id}", response_model=List[ChemoCycleResponse])
async def list_cycles(case_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return db.query(ChemoCycle).filter(ChemoCycle.case_id == case_id).order_by(ChemoCycle.cycle_number).all()


@router.patch("/chemo-cycles/{cycle_id}", response_model=ChemoCycleResponse)
async def update_cycle(cycle_id: int, data: ChemoCycleUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    cycle = db.query(ChemoCycle).filter(ChemoCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    from datetime import datetime, timezone
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(cycle, k, v)
    if data.status and data.status.value == "administered" and not cycle.administered_at:
        cycle.administered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=201)
async def add_follow_up(data: FollowUpCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    follow_up = OncologyFollowUp(**data.model_dump())
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.get("/follow-ups/case/{case_id}", response_model=List[FollowUpResponse])
async def list_follow_ups(case_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return db.query(OncologyFollowUp).filter(
        OncologyFollowUp.case_id == case_id
    ).order_by(OncologyFollowUp.visit_date.desc()).all()
