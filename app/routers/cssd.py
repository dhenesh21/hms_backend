from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.cssd import SterilizationCycle, CycleStatus
from app.models.user import User
from app.schemas.cssd import CycleCreate, CycleResponse, QualityCheckRequest, DispatchRequest

router = APIRouter(prefix="/cssd", tags=["CSSD"])


@router.post("/cycles", response_model=CycleResponse, status_code=201)
async def receive_items(
    data: CycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle_data = data.model_dump()
    cycle_data["received_by"] = current_user.id

    attempt_base = next_sequence_number(db, SterilizationCycle)
    cycle = None
    last_error = None
    for i in range(MAX_RETRIES):
        cycle_data["cycle_number"] = f"CSSD{attempt_base + i:06d}"
        cycle = SterilizationCycle(**cycle_data)
        db.add(cycle)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            cycle = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/cycles", response_model=list[CycleResponse])
async def list_cycles(
    status: Optional[CycleStatus] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(SterilizationCycle)
    if status:
        q = q.filter(SterilizationCycle.status == status)
    return q.order_by(SterilizationCycle.received_at.desc()).limit(limit).all()


@router.get("/cycles/active", response_model=list[CycleResponse])
async def active_cycles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(SterilizationCycle)
        .filter(~SterilizationCycle.status.in_([CycleStatus.DISPATCHED, CycleStatus.FAILED]))
        .order_by(SterilizationCycle.received_at.asc())
        .all()
    )


@router.put("/cycles/{cycle_id}/start-sterilization", response_model=CycleResponse)
async def start_sterilization(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = db.query(SterilizationCycle).filter(SterilizationCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Sterilization cycle not found")
    if cycle.status not in (CycleStatus.RECEIVED, CycleStatus.WASHING):
        raise HTTPException(status_code=400, detail=f"Cannot start sterilization from status '{cycle.status.value}'")

    cycle.status = CycleStatus.STERILIZING
    cycle.sterilization_start = datetime.utcnow()
    db.commit()
    db.refresh(cycle)
    return cycle


@router.put("/cycles/{cycle_id}/quality-check", response_model=CycleResponse)
async def quality_check(
    cycle_id: int,
    data: QualityCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = db.query(SterilizationCycle).filter(SterilizationCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Sterilization cycle not found")
    if cycle.status != CycleStatus.STERILIZING:
        raise HTTPException(status_code=400, detail="Cycle must be in sterilizing status before quality check")

    cycle.sterilization_end = datetime.utcnow()
    cycle.quality_check_passed = "pass" if data.passed else "fail"
    cycle.status = CycleStatus.READY if data.passed else CycleStatus.FAILED
    if data.notes:
        cycle.notes = f"{cycle.notes or ''}\nQC: {data.notes}".strip()
    db.commit()
    db.refresh(cycle)
    return cycle


@router.put("/cycles/{cycle_id}/dispatch", response_model=CycleResponse)
async def dispatch_cycle(
    cycle_id: int,
    data: DispatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = db.query(SterilizationCycle).filter(SterilizationCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Sterilization cycle not found")
    if cycle.status != CycleStatus.READY:
        raise HTTPException(status_code=400, detail="Only cycles that passed quality check can be dispatched")

    cycle.status = CycleStatus.DISPATCHED
    cycle.dispatched_at = datetime.utcnow()
    cycle.dispatched_to = data.dispatched_to
    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/dashboard/stats")
async def cssd_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    in_process = (
        db.query(SterilizationCycle)
        .filter(SterilizationCycle.status.in_([CycleStatus.RECEIVED, CycleStatus.WASHING, CycleStatus.STERILIZING, CycleStatus.QUALITY_CHECK]))
        .count()
    )
    ready_for_dispatch = db.query(SterilizationCycle).filter(SterilizationCycle.status == CycleStatus.READY).count()
    failed_cycles = db.query(SterilizationCycle).filter(SterilizationCycle.status == CycleStatus.FAILED).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    dispatched_today = (
        db.query(SterilizationCycle)
        .filter(SterilizationCycle.status == CycleStatus.DISPATCHED, SterilizationCycle.dispatched_at >= today_start)
        .count()
    )

    return {
        "in_process": in_process,
        "ready_for_dispatch": ready_for_dispatch,
        "failed_cycles": failed_cycles,
        "dispatched_today": dispatched_today,
    }
