from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.front_desk import Visitor, LostFoundItem, VisitorStatus, LostFoundStatus
from app.models.patient import Patient
from app.models.user import User
from app.schemas.front_desk import (
    VisitorCheckIn,
    VisitorResponse,
    LostFoundCreate,
    LostFoundClaim,
    LostFoundResponse,
)

router = APIRouter(prefix="/front-desk", tags=["Visitor Management & Lost Found"])


# ── VISITOR MANAGEMENT ─────────────────────────────────────────────

@router.post("/visitors/check-in", response_model=VisitorResponse, status_code=201)
async def check_in_visitor(
    data: VisitorCheckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visitor_data = data.model_dump()
    visitor_data["issued_by"] = current_user.id

    attempt_base = next_sequence_number(db, Visitor)
    visitor = None
    last_error = None
    for i in range(MAX_RETRIES):
        visitor_data["pass_number"] = f"VIS{attempt_base + i:06d}"
        visitor = Visitor(**visitor_data)
        db.add(visitor)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            visitor = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(visitor)
    return visitor


@router.get("/visitors", response_model=list[VisitorResponse])
async def list_visitors(
    status: Optional[VisitorStatus] = Query(None),
    patient_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Visitor)
    if status:
        q = q.filter(Visitor.status == status)
    if patient_id:
        q = q.filter(Visitor.patient_id == patient_id)
    return q.order_by(Visitor.check_in_time.desc()).limit(limit).all()


@router.get("/visitors/currently-in", response_model=list[VisitorResponse])
async def currently_in_visitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Visitor)
        .filter(Visitor.status == VisitorStatus.CHECKED_IN)
        .order_by(Visitor.check_in_time.asc())
        .all()
    )


@router.put("/visitors/{visitor_id}/check-out", response_model=VisitorResponse)
async def check_out_visitor(
    visitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor record not found")
    if visitor.status == VisitorStatus.CHECKED_OUT:
        raise HTTPException(status_code=400, detail="Visitor has already checked out")

    visitor.status = VisitorStatus.CHECKED_OUT
    visitor.check_out_time = datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    return visitor


# ── LOST & FOUND ─────────────────────────────────────────────

@router.post("/lost-found", response_model=LostFoundResponse, status_code=201)
async def report_lost_found(
    data: LostFoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item_data = data.model_dump()
    item_data["logged_by"] = current_user.id

    attempt_base = next_sequence_number(db, LostFoundItem)
    item = None
    last_error = None
    for i in range(MAX_RETRIES):
        item_data["item_number"] = f"LF{attempt_base + i:06d}"
        item = LostFoundItem(**item_data)
        db.add(item)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            item = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(item)
    return item


@router.get("/lost-found", response_model=list[LostFoundResponse])
async def list_lost_found(
    status: Optional[LostFoundStatus] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(LostFoundItem)
    if status:
        q = q.filter(LostFoundItem.status == status)
    return q.order_by(LostFoundItem.date_reported.desc()).limit(limit).all()


@router.put("/lost-found/{item_id}/claim", response_model=LostFoundResponse)
async def claim_item(
    item_id: int,
    data: LostFoundClaim,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lost & found item not found")
    if item.status == LostFoundStatus.CLAIMED:
        raise HTTPException(status_code=400, detail="This item has already been claimed")

    item.status = LostFoundStatus.CLAIMED
    item.claimed_by = data.claimed_by
    item.claim_verification = data.claim_verification
    item.claimed_date = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


@router.put("/lost-found/{item_id}/mark-unclaimed", response_model=LostFoundResponse)
async def mark_unclaimed(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an item as unclaimed after the retention period - it can then
    be disposed/donated per hospital policy."""
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lost & found item not found")
    if item.status != LostFoundStatus.REPORTED:
        raise HTTPException(status_code=400, detail=f"Cannot mark unclaimed from status '{item.status.value}'")

    item.status = LostFoundStatus.UNCLAIMED
    db.commit()
    db.refresh(item)
    return item


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def front_desk_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    visitors_currently_in = db.query(Visitor).filter(Visitor.status == VisitorStatus.CHECKED_IN).count()
    visitors_today = db.query(Visitor).filter(Visitor.check_in_time >= today_start).count()
    pending_lost_found = db.query(LostFoundItem).filter(LostFoundItem.status == LostFoundStatus.REPORTED).count()
    claimed_this_month = (
        db.query(LostFoundItem)
        .filter(
            LostFoundItem.status == LostFoundStatus.CLAIMED,
            LostFoundItem.claimed_date >= today_start.replace(day=1),
        )
        .count()
    )

    return {
        "visitors_currently_in": visitors_currently_in,
        "visitors_today": visitors_today,
        "pending_lost_found": pending_lost_found,
        "claimed_this_month": claimed_this_month,
    }
