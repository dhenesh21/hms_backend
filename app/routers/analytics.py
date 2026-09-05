"""
Items 274-276 (Operational/Clinical/Financial Analytics). The 266-270
dashboards (verified this session) already give real-time snapshots -
"how many patients right now." What was actually missing is what
analytics specifically means versus a dashboard: trends over time and
comparisons, not just a current count. Every endpoint here groups by a
time bucket (day/week/month) or a dimension (department, diagnosis) so
the response is a series/breakdown, not a single number - that's the
concrete difference from Batch 266-270's dashboards, which this module
deliberately doesn't duplicate.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Date, case
from typing import Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.opd import OPDVisit
from app.models.ipd import IPDAdmission, IPDStatus
from app.models.emr import DiagnosisRecord
from app.models.billing import Bill, Payment

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _default_range(from_date: Optional[date], to_date: Optional[date]):
    td = to_date or date.today()
    fd = from_date or (td - timedelta(days=90))
    return fd, td


# ── OPERATIONAL ANALYTICS (item 274) ────────────────────
@router.get("/operational/patient-flow-trend")
async def patient_flow_trend(from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Daily OPD visits + IPD admissions over the range - the trend line a
    single dashboard count can't show (is volume rising or falling?)."""
    fd, td = _default_range(from_date, to_date)

    opd_by_day = dict(
        db.query(func.cast(OPDVisit.visit_date, Date), func.count(OPDVisit.id))
        .filter(func.cast(OPDVisit.visit_date, Date).between(fd, td))
        .group_by(func.cast(OPDVisit.visit_date, Date)).all()
    )
    ipd_by_day = dict(
        db.query(func.cast(IPDAdmission.admission_date, Date), func.count(IPDAdmission.id))
        .filter(func.cast(IPDAdmission.admission_date, Date).between(fd, td))
        .group_by(func.cast(IPDAdmission.admission_date, Date)).all()
    )

    days = [(fd + timedelta(days=i)) for i in range((td - fd).days + 1)]
    return {
        "from_date": fd, "to_date": td,
        "series": [
            {"date": d.isoformat(), "opd_visits": opd_by_day.get(d, 0), "ipd_admissions": ipd_by_day.get(d, 0)}
            for d in days
        ],
    }


@router.get("/operational/bed-occupancy-trend")
async def bed_occupancy_trend(from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                               db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Admissions vs discharges per day - where occupancy is actually
    heading, not just today's snapshot count."""
    fd, td = _default_range(from_date, to_date)

    admissions_by_day = dict(
        db.query(func.cast(IPDAdmission.admission_date, Date), func.count(IPDAdmission.id))
        .filter(func.cast(IPDAdmission.admission_date, Date).between(fd, td))
        .group_by(func.cast(IPDAdmission.admission_date, Date)).all()
    )
    discharges_by_day = dict(
        db.query(func.cast(IPDAdmission.discharge_date, Date), func.count(IPDAdmission.id))
        .filter(IPDAdmission.discharge_date.isnot(None),
                func.cast(IPDAdmission.discharge_date, Date).between(fd, td))
        .group_by(func.cast(IPDAdmission.discharge_date, Date)).all()
    )

    days = [(fd + timedelta(days=i)) for i in range((td - fd).days + 1)]
    return {
        "from_date": fd, "to_date": td,
        "series": [
            {"date": d.isoformat(), "admissions": admissions_by_day.get(d, 0), "discharges": discharges_by_day.get(d, 0)}
            for d in days
        ],
    }


# ── CLINICAL ANALYTICS (item 275) ───────────────────────
@router.get("/clinical/top-diagnoses")
async def top_diagnoses(from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                         limit: int = Query(15, le=50),
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Most frequent diagnoses in the period - a breakdown, not a count,
    which is what turns raw diagnosis records into something a clinical
    lead can actually act on (case-mix shift, an outbreak pattern, etc)."""
    fd, td = _default_range(from_date, to_date)
    rows = (
        db.query(DiagnosisRecord.diagnosis, DiagnosisRecord.icd_code, func.count(DiagnosisRecord.id).label("count"))
        .filter(DiagnosisRecord.diagnosis_date.between(fd, td))
        .group_by(DiagnosisRecord.diagnosis, DiagnosisRecord.icd_code)
        .order_by(func.count(DiagnosisRecord.id).desc())
        .limit(limit).all()
    )
    return {"from_date": fd, "to_date": td,
            "diagnoses": [{"diagnosis": r[0], "icd_code": r[1], "count": r[2]} for r in rows]}


@router.get("/clinical/readmission-rate")
async def readmission_rate(within_days: int = Query(30, le=90),
                            from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                            db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    % of discharges in the period followed by a same-patient readmission
    within `within_days` - computed by comparing each patient's admission
    dates against their own prior discharge, not a stored flag, so it
    reflects real IPDAdmission history rather than needing every discharge
    to be manually tagged.
    """
    fd, td = _default_range(from_date, to_date)
    discharged = db.query(IPDAdmission).filter(
        IPDAdmission.discharge_date.isnot(None),
        func.cast(IPDAdmission.discharge_date, Date).between(fd, td),
    ).all()

    readmitted_count = 0
    for d in discharged:
        window_end = d.discharge_date.date() + timedelta(days=within_days)
        next_admission = db.query(IPDAdmission).filter(
            IPDAdmission.patient_id == d.patient_id,
            IPDAdmission.id != d.id,
            func.cast(IPDAdmission.admission_date, Date) > d.discharge_date.date(),
            func.cast(IPDAdmission.admission_date, Date) <= window_end,
        ).first()
        if next_admission:
            readmitted_count += 1

    total = len(discharged)
    return {
        "from_date": fd, "to_date": td, "within_days": within_days,
        "total_discharges": total, "readmitted": readmitted_count,
        "readmission_rate_percent": round((readmitted_count / total * 100), 2) if total else 0,
    }


# ── FINANCIAL ANALYTICS (item 276) ──────────────────────
@router.get("/financial/revenue-trend")
async def revenue_trend(from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                         bucket: str = Query("day", regex="^(day|week|month)$"),
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Billed vs collected revenue over time, bucketed - the 266-270
    dashboards show today's collection; this shows the trend that number
    sits within."""
    fd, td = _default_range(from_date, to_date)

    if bucket == "day":
        bucket_expr = func.cast(Bill.bill_date, Date)
    elif bucket == "week":
        bucket_expr = func.date_trunc("week", Bill.bill_date) if db.bind.dialect.name == "postgresql" else func.cast(Bill.bill_date, Date)
    else:
        bucket_expr = func.date_trunc("month", Bill.bill_date) if db.bind.dialect.name == "postgresql" else func.cast(Bill.bill_date, Date)

    rows = (
        db.query(bucket_expr.label("bucket"), func.sum(Bill.gross_total), func.sum(Bill.paid_amount))
        .filter(func.cast(Bill.bill_date, Date).between(fd, td))
        .group_by("bucket").order_by("bucket").all()
    )
    return {
        "from_date": fd, "to_date": td, "bucket": bucket,
        "series": [
            {"period": str(r[0]), "billed": round(r[1] or 0, 2), "collected": round(r[2] or 0, 2)}
            for r in rows
        ],
    }


@router.get("/financial/payment-mode-breakdown")
async def payment_mode_breakdown(from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
                                  db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """How revenue splits across cash/card/UPI/insurance etc - a
    comparison dashboards don't show since they report one total."""
    fd, td = _default_range(from_date, to_date)
    rows = (
        db.query(Payment.payment_mode, func.sum(Payment.amount), func.count(Payment.id))
        .filter(func.cast(Payment.payment_date, Date).between(fd, td), Payment.amount > 0)
        .group_by(Payment.payment_mode).all()
    )
    return {"from_date": fd, "to_date": td,
            "breakdown": [{"payment_mode": r[0], "total_amount": round(r[1] or 0, 2), "transaction_count": r[2]} for r in rows]}
