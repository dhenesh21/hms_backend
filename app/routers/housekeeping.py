from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.housekeeping import CleaningTask, LinenLog, WasteLog, CleaningTaskStatus, WasteType
from app.models.ipd import Bed, BedStatus
from app.models.user import User
from app.schemas.housekeeping import (
    CleaningTaskCreate,
    CleaningTaskResponse,
    LinenLogCreate,
    LinenLogReceive,
    LinenLogResponse,
    WasteLogCreate,
    WasteLogDispose,
    WasteLogResponse,
)

router = APIRouter(prefix="/housekeeping", tags=["Housekeeping"])


# ── CLEANING TASKS ─────────────────────────────────────────────

@router.post("/tasks", response_model=CleaningTaskResponse, status_code=201)
async def create_task(
    data: CleaningTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.bed_id:
        bed = db.query(Bed).filter(Bed.id == data.bed_id).first()
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")

    task = CleaningTask(**data.model_dump(), created_by=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks", response_model=list[CleaningTaskResponse])
async def list_tasks(
    status: Optional[CleaningTaskStatus] = Query(None),
    ward_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CleaningTask)
    if status:
        q = q.filter(CleaningTask.status == status)
    if ward_id:
        q = q.filter(CleaningTask.ward_id == ward_id)
    return q.order_by(CleaningTask.scheduled_at.desc()).limit(limit).all()


@router.get("/tasks/pending", response_model=list[CleaningTaskResponse])
async def pending_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CleaningTask)
        .filter(CleaningTask.status.in_([CleaningTaskStatus.PENDING, CleaningTaskStatus.IN_PROGRESS]))
        .order_by(CleaningTask.scheduled_at.asc())
        .all()
    )


@router.put("/tasks/{task_id}/start", response_model=CleaningTaskResponse)
async def start_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(CleaningTask).filter(CleaningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Cleaning task not found")
    if task.status != CleaningTaskStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot start a task with status '{task.status.value}'")

    task.status = CleaningTaskStatus.IN_PROGRESS
    task.started_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}/complete", response_model=CleaningTaskResponse)
async def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(CleaningTask).filter(CleaningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Cleaning task not found")
    if task.status not in (CleaningTaskStatus.PENDING, CleaningTaskStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail=f"Cannot complete a task with status '{task.status.value}'")

    task.status = CleaningTaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()

    # This is what closes the loop with IPD: a bed that was in CLEANING
    # status (set when the patient was discharged) becomes AVAILABLE again
    # only once its cleaning task is actually completed here.
    if task.bed_id:
        bed = db.query(Bed).filter(Bed.id == task.bed_id).first()
        if bed and bed.status == BedStatus.CLEANING:
            bed.status = BedStatus.AVAILABLE
            if bed.ward:
                bed.ward.available_beds += 1

    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}/verify", response_model=CleaningTaskResponse)
async def verify_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supervisor sign-off - roadmap-level quality check on completed cleaning."""
    task = db.query(CleaningTask).filter(CleaningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Cleaning task not found")
    if task.status != CleaningTaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task must be completed before it can be verified")

    task.status = CleaningTaskStatus.VERIFIED
    task.verified_at = datetime.utcnow()
    task.verified_by = current_user.id
    db.commit()
    db.refresh(task)
    return task


# ── LINEN TRACKING ─────────────────────────────────────────────

@router.post("/linen", response_model=LinenLogResponse, status_code=201)
async def send_linen(
    data: LinenLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = LinenLog(**data.model_dump(), logged_by=current_user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/linen", response_model=list[LinenLogResponse])
async def list_linen_logs(
    ward_id: Optional[int] = Query(None),
    pending_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(LinenLog)
    if ward_id:
        q = q.filter(LinenLog.ward_id == ward_id)
    if pending_only:
        q = q.filter(LinenLog.received_at.is_(None))
    return q.order_by(LinenLog.sent_at.desc()).all()


@router.put("/linen/{log_id}/receive", response_model=LinenLogResponse)
async def receive_linen(
    log_id: int,
    data: LinenLogReceive,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(LinenLog).filter(LinenLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Linen log not found")
    if log.received_at:
        raise HTTPException(status_code=400, detail="This linen batch has already been received")

    log.quantity_received = data.quantity_received
    log.received_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


# ── WASTE MANAGEMENT ─────────────────────────────────────────────

@router.post("/waste", response_model=WasteLogResponse, status_code=201)
async def log_waste_collection(
    data: WasteLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = WasteLog(**data.model_dump(), collected_by=current_user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/waste", response_model=list[WasteLogResponse])
async def list_waste_logs(
    waste_type: Optional[WasteType] = Query(None),
    pending_disposal: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(WasteLog)
    if waste_type:
        q = q.filter(WasteLog.waste_type == waste_type)
    if pending_disposal:
        q = q.filter(WasteLog.disposed_at.is_(None))
    return q.order_by(WasteLog.collected_at.desc()).all()


@router.put("/waste/{log_id}/dispose", response_model=WasteLogResponse)
async def dispose_waste(
    log_id: int,
    data: WasteLogDispose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(WasteLog).filter(WasteLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Waste log not found")
    if log.disposed_at:
        raise HTTPException(status_code=400, detail="This waste has already been marked disposed")

    log.disposal_method = data.disposal_method
    log.disposed_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def housekeeping_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pending_tasks_count = (
        db.query(CleaningTask)
        .filter(CleaningTask.status.in_([CleaningTaskStatus.PENDING, CleaningTaskStatus.IN_PROGRESS]))
        .count()
    )
    beds_awaiting_cleaning = db.query(Bed).filter(Bed.status == BedStatus.CLEANING).count()
    pending_linen = db.query(LinenLog).filter(LinenLog.received_at.is_(None)).count()
    pending_waste_disposal = db.query(WasteLog).filter(WasteLog.disposed_at.is_(None)).count()
    biomedical_waste_pending = (
        db.query(WasteLog)
        .filter(WasteLog.waste_type == WasteType.BIOMEDICAL, WasteLog.disposed_at.is_(None))
        .count()
    )

    return {
        "pending_tasks": pending_tasks_count,
        "beds_awaiting_cleaning": beds_awaiting_cleaning,
        "pending_linen_returns": pending_linen,
        "pending_waste_disposal": pending_waste_disposal,
        "biomedical_waste_pending": biomedical_waste_pending,
    }
