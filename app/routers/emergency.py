from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.emergency import ERVisit, ERTriage, EREmergencyTreatment, ERVisitStatus, TriageLevel
from app.models.user import User
from app.schemas.emergency import (
    ERVisitCreate,
    ERVisitUpdate,
    ERVisitResponse,
    ERVisitDetailResponse,
    TriageCreate,
    TriageResponse,
    TreatmentCreate,
    TreatmentResponse,
)

router = APIRouter(prefix="/emergency", tags=["Emergency"])


@router.post("/visits", response_model=ERVisitDetailResponse, status_code=201)
async def register_er_visit(
    data: ERVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.exc import IntegrityError

    triage_data = data.triage
    visit_data = data.model_dump(exclude={"triage"})
    visit_data["created_by"] = current_user.id

    attempt_base = next_sequence_number(db, ERVisit)
    visit = None
    last_error = None
    for i in range(MAX_RETRIES):
        visit_data["er_number"] = f"ER{attempt_base + i:07d}"
        visit = ERVisit(**visit_data)
        db.add(visit)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            visit = None
    if last_error:
        raise last_error

    if triage_data:
        triage = ERTriage(
            **triage_data.model_dump(),
            er_visit_id=visit.id,
            triaged_by=current_user.id,
        )
        db.add(triage)
        visit.status = ERVisitStatus.IN_TRIAGE

    db.commit()
    db.refresh(visit)
    return visit


@router.get("/visits", response_model=list[ERVisitResponse])
async def list_er_visits(
    status: Optional[ERVisitStatus] = Query(None),
    is_mlc: Optional[bool] = Query(None),
    patient_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ERVisit)
    if status:
        q = q.filter(ERVisit.status == status)
    if is_mlc is not None:
        q = q.filter(ERVisit.is_mlc == is_mlc)
    if patient_id:
        q = q.filter(ERVisit.patient_id == patient_id)
    return q.order_by(ERVisit.arrival_time.desc()).limit(limit).all()


@router.get("/visits/active", response_model=list[ERVisitResponse])
async def active_er_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Live ER queue - anything not yet discharged/admitted/deceased/LWOT."""
    closed_statuses = [
        ERVisitStatus.DISCHARGED,
        ERVisitStatus.ADMITTED,
        ERVisitStatus.REFERRED_OUT,
        ERVisitStatus.DECEASED,
        ERVisitStatus.LEFT_WITHOUT_TREATMENT,
    ]
    return (
        db.query(ERVisit)
        .filter(~ERVisit.status.in_(closed_statuses))
        .order_by(ERVisit.arrival_time.asc())
        .all()
    )


@router.get("/visits/{visit_id}", response_model=ERVisitDetailResponse)
async def get_er_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = db.query(ERVisit).filter(ERVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="ER visit not found")
    return visit


@router.put("/visits/{visit_id}", response_model=ERVisitResponse)
async def update_er_visit(
    visit_id: int,
    data: ERVisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = db.query(ERVisit).filter(ERVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="ER visit not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(visit, field, value)

    if data.status in (
        ERVisitStatus.DISCHARGED,
        ERVisitStatus.REFERRED_OUT,
        ERVisitStatus.DECEASED,
        ERVisitStatus.LEFT_WITHOUT_TREATMENT,
    ):
        from datetime import datetime
        visit.discharge_time = datetime.utcnow()

    db.commit()
    db.refresh(visit)
    return visit


@router.post("/visits/{visit_id}/triage", response_model=TriageResponse, status_code=201)
async def add_triage(
    visit_id: int,
    data: TriageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = db.query(ERVisit).filter(ERVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="ER visit not found")

    existing = db.query(ERTriage).filter(ERTriage.er_visit_id == visit_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Triage already recorded for this visit")

    triage = ERTriage(**data.model_dump(), er_visit_id=visit_id, triaged_by=current_user.id)
    db.add(triage)
    visit.status = ERVisitStatus.IN_TRIAGE
    db.commit()
    db.refresh(triage)
    return triage


@router.post("/visits/{visit_id}/treatments", response_model=TreatmentResponse, status_code=201)
async def add_treatment(
    visit_id: int,
    data: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = db.query(ERVisit).filter(ERVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="ER visit not found")

    treatment = EREmergencyTreatment(
        **data.model_dump(), er_visit_id=visit_id, given_by=current_user.id
    )
    db.add(treatment)
    if visit.status in (ERVisitStatus.WAITING, ERVisitStatus.IN_TRIAGE):
        visit.status = ERVisitStatus.IN_TREATMENT
    db.commit()
    db.refresh(treatment)
    return treatment


@router.get("/mlc-register", response_model=list[ERVisitResponse])
async def mlc_register(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Medico-Legal Case register - roadmap's 'MLC Register' + 'Accident Register'."""
    return (
        db.query(ERVisit)
        .filter(ERVisit.is_mlc == True)  # noqa: E712
        .order_by(ERVisit.arrival_time.desc())
        .limit(limit)
        .all()
    )


@router.get("/dashboard/stats")
async def emergency_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = db.query(ERVisit).filter(ERVisit.arrival_time >= today_start).count()
    active = (
        db.query(ERVisit)
        .filter(
            ~ERVisit.status.in_(
                [
                    ERVisitStatus.DISCHARGED,
                    ERVisitStatus.ADMITTED,
                    ERVisitStatus.REFERRED_OUT,
                    ERVisitStatus.DECEASED,
                    ERVisitStatus.LEFT_WITHOUT_TREATMENT,
                ]
            )
        )
        .count()
    )
    critical = (
        db.query(ERVisit)
        .join(ERTriage, ERTriage.er_visit_id == ERVisit.id)
        .filter(ERTriage.triage_level == TriageLevel.LEVEL_1_RESUSCITATION)
        .filter(
            ~ERVisit.status.in_(
                [ERVisitStatus.DISCHARGED, ERVisitStatus.ADMITTED, ERVisitStatus.DECEASED]
            )
        )
        .count()
    )
    mlc_today = (
        db.query(ERVisit)
        .filter(ERVisit.arrival_time >= today_start, ERVisit.is_mlc == True)  # noqa: E712
        .count()
    )

    return {
        "total_visits_today": total_today,
        "active_in_er": active,
        "critical_active": critical,
        "mlc_cases_today": mlc_today,
    }
