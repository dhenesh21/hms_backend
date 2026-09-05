from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date as dt_date
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.ot import OperationTheatre, Surgery, OTConsumable, OTStatus, SurgeryStatus
from app.models.user import User
from app.schemas.ot_radiology import (
    OTCreate, OTResponse,
    SurgeryCreate, SurgeryUpdate, SurgeryResponse,
    OTConsumableCreate, OTConsumableResponse
)

router = APIRouter(prefix="/ot", tags=["Operation Theatre"])


# ── OPERATION THEATRES ────────────────────────────────
@router.post("/theatres", response_model=OTResponse, status_code=201)
async def create_ot(data: OTCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    ot = OperationTheatre(**data.model_dump())
    db.add(ot)
    db.commit()
    db.refresh(ot)
    return ot


@router.get("/theatres", response_model=list[OTResponse])
async def list_ots(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    return db.query(OperationTheatre).filter(OperationTheatre.is_active == True).all()


@router.put("/theatres/{ot_id}/status")
async def update_ot_status(ot_id: int, status: OTStatus,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    ot = db.query(OperationTheatre).filter(OperationTheatre.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    ot.status = status
    db.commit()
    return {"message": f"OT status updated to {status}"}


# ── SURGERY SCHEDULING ────────────────────────────────
@router.post("/surgeries", response_model=SurgeryResponse, status_code=201)
async def schedule_surgery(data: SurgeryCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    # Check OT availability
    conflict = db.query(Surgery).filter(
        Surgery.ot_id == data.ot_id,
        Surgery.surgery_date == data.surgery_date,
        Surgery.status.notin_([SurgeryStatus.CANCELLED, SurgeryStatus.POSTPONED]),
        Surgery.scheduled_start_time == data.scheduled_start_time
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="OT already booked at this time")

    from sqlalchemy.exc import IntegrityError

    surgery_data = data.model_dump()
    surgery_data['assistant_surgeon_ids'] = data.assistant_surgeon_ids
    surgery_data['scheduled_by'] = current_user.id

    attempt_base = next_sequence_number(db, Surgery)
    surgery = None
    last_error = None
    for i in range(MAX_RETRIES):
        surgery_data["surgery_number"] = f"OT{attempt_base + i:07d}"
        surgery = Surgery(**surgery_data)
        db.add(surgery)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            surgery = None
    if last_error:
        raise last_error

    # Mark OT as booked
    ot = db.query(OperationTheatre).filter(OperationTheatre.id == data.ot_id).first()
    if ot:
        ot.status = OTStatus.BOOKED

    db.commit()
    db.refresh(surgery)
    return surgery


@router.get("/surgeries", response_model=list[SurgeryResponse])
async def list_surgeries(surgery_date: Optional[dt_date] = Query(None),
                         status: Optional[SurgeryStatus] = Query(None),
                         patient_id: Optional[int] = Query(None),
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    query = db.query(Surgery)
    if surgery_date:
        query = query.filter(Surgery.surgery_date == surgery_date)
    if status:
        query = query.filter(Surgery.status == status)
    if patient_id:
        query = query.filter(Surgery.patient_id == patient_id)
    return query.order_by(Surgery.surgery_date.desc(), Surgery.scheduled_start_time).limit(100).all()


@router.get("/surgeries/today")
async def today_surgeries(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    today = dt_date.today()
    surgeries = db.query(Surgery).filter(Surgery.surgery_date == today).all()
    return [{
        "id": s.id, "surgery_number": s.surgery_number,
        "patient_id": s.patient_id,
        "patient_name": f"{s.patient.first_name} {s.patient.last_name}" if s.patient else None,
        "ot_id": s.ot_id,
        "ot_name": s.ot.name if s.ot else None,
        "procedure_name": s.procedure_name,
        "scheduled_start_time": s.scheduled_start_time,
        "scheduled_end_time": s.scheduled_end_time,
        "status": s.status,
        "primary_surgeon_id": s.primary_surgeon_id,
        "anesthesia_type": s.anesthesia_type
    } for s in surgeries]


@router.get("/surgeries/{surgery_id}", response_model=SurgeryResponse)
async def get_surgery(surgery_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    s = db.query(Surgery).filter(Surgery.id == surgery_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Surgery not found")
    return s


@router.put("/surgeries/{surgery_id}", response_model=SurgeryResponse)
async def update_surgery(surgery_id: int, data: SurgeryUpdate,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    surgery = db.query(Surgery).filter(Surgery.id == surgery_id).first()
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(surgery, field, value)

    # Auto duration calc on completion
    if data.actual_start_time and data.actual_end_time:
        delta = data.actual_end_time - data.actual_start_time
        surgery.duration_minutes = int(delta.total_seconds() / 60)

    # Auto OT status on completion/cancel
    if data.status in [SurgeryStatus.COMPLETED, SurgeryStatus.CANCELLED]:
        ot = db.query(OperationTheatre).filter(OperationTheatre.id == surgery.ot_id).first()
        if ot:
            ot.status = OTStatus.CLEANING if data.status == SurgeryStatus.COMPLETED else OTStatus.AVAILABLE

    db.commit()
    db.refresh(surgery)
    return surgery


# ── PRE-OP CHECKLIST ──────────────────────────────────
@router.put("/surgeries/{surgery_id}/pre-op-complete")
async def complete_pre_op(surgery_id: int,
                          checklist: dict,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    surgery = db.query(Surgery).filter(Surgery.id == surgery_id).first()
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    surgery.pre_op_checklist = checklist
    surgery.pre_op_completed_at = datetime.utcnow()
    surgery.pre_op_completed_by = current_user.id
    surgery.status = SurgeryStatus.PRE_OP
    db.commit()
    return {"message": "Pre-op checklist completed"}


# ── CONSUMABLES ───────────────────────────────────────
@router.post("/consumables", response_model=OTConsumableResponse, status_code=201)
async def add_consumable(data: OTConsumableCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    consumable_data = data.model_dump()
    consumable_data['total_cost'] = data.quantity_used * data.unit_cost
    consumable = OTConsumable(**consumable_data)
    db.add(consumable)
    db.commit()
    db.refresh(consumable)
    return consumable


@router.get("/consumables/{surgery_id}", response_model=list[OTConsumableResponse])
async def get_consumables(surgery_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(OTConsumable).filter(OTConsumable.surgery_id == surgery_id).all()


# ── DASHBOARD ─────────────────────────────────────────
@router.get("/dashboard/stats")
async def ot_stats(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    today = dt_date.today()
    today_count = db.query(Surgery).filter(Surgery.surgery_date == today).count()
    in_progress = db.query(Surgery).filter(Surgery.status == SurgeryStatus.IN_PROGRESS).count()
    scheduled = db.query(Surgery).filter(
        Surgery.surgery_date == today,
        Surgery.status == SurgeryStatus.SCHEDULED
    ).count()
    available_ots = db.query(OperationTheatre).filter(
        OperationTheatre.status == OTStatus.AVAILABLE,
        OperationTheatre.is_active == True
    ).count()
    return {
        "today_surgeries": today_count,
        "in_progress": in_progress,
        "scheduled_today": scheduled,
        "available_ots": available_ots
    }


