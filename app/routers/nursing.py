from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nursing import (MedicationAdministrationRecord, MedicationAdministration,
                                  NursingAssessment, CarePlan, CareIntervention,
                                  ShiftHandover, AdministrationStatus)
from app.models.user import User
from app.schemas.nursing import (
    MARCreate, MARResponse,
    AdministrationRecord, AdministrationResponse,
    NursingAssessmentCreate, NursingAssessmentResponse,
    CarePlanCreate, CarePlanUpdate, CarePlanResponse,
    CareInterventionCreate,
    ShiftHandoverCreate, ShiftHandoverResponse
)

router = APIRouter(prefix="/nursing", tags=["Nursing"])


# ── MEDICATION ADMINISTRATION RECORD (MAR) ────────────
@router.post("/mar", response_model=MARResponse, status_code=201)
async def create_mar(data: MARCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    mar = MedicationAdministrationRecord(**data.model_dump())
    db.add(mar)
    db.commit()
    db.refresh(mar)
    # Auto-generate scheduled administrations for today
    _generate_schedules(db, mar)
    return mar


def _generate_schedules(db: Session, mar: MedicationAdministrationRecord):
    """Generate today's scheduled dose records"""
    today = date.today()
    for time_str in mar.scheduled_times:
        try:
            hour, minute = map(int, time_str.split(":"))
            scheduled_dt = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
            existing = db.query(MedicationAdministration).filter(
                MedicationAdministration.mar_id == mar.id,
                MedicationAdministration.scheduled_datetime == scheduled_dt
            ).first()
            if not existing:
                admin = MedicationAdministration(
                    mar_id=mar.id,
                    scheduled_datetime=scheduled_dt,
                    status=AdministrationStatus.SCHEDULED
                )
                db.add(admin)
        except:
            pass
    db.commit()


@router.get("/mar/{admission_id}", response_model=list[MARResponse])
async def get_mar_for_admission(admission_id: int,
                                 active_only: bool = Query(True),
                                 db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    q = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.ipd_admission_id == admission_id)
    if active_only:
        q = q.filter(MedicationAdministrationRecord.is_active == True)
    return q.all()


@router.delete("/mar/{mar_id}")
async def discontinue_mar(mar_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    mar = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.id == mar_id).first()
    if not mar:
        raise HTTPException(status_code=404, detail="MAR not found")
    mar.is_active = False
    mar.end_date = date.today()
    db.commit()
    return {"message": "Medication discontinued"}


# ── MEDICATION ADMINISTRATION ─────────────────────────
@router.post("/administer", response_model=AdministrationResponse, status_code=201)
async def record_administration(data: AdministrationRecord,
                                 db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    # Find existing scheduled record or create new
    admin = db.query(MedicationAdministration).filter(
        MedicationAdministration.mar_id == data.mar_id,
        MedicationAdministration.scheduled_datetime == data.scheduled_datetime
    ).first()

    if admin:
        admin.status = data.status
        admin.administered_datetime = datetime.utcnow() if data.status == AdministrationStatus.GIVEN else None
        admin.administered_by = current_user.id
        admin.dose_given = data.dose_given
        admin.remarks = data.remarks
        admin.reason_not_given = data.reason_not_given
    else:
        admin = MedicationAdministration(
            mar_id=data.mar_id,
            scheduled_datetime=data.scheduled_datetime,
            status=data.status,
            administered_datetime=datetime.utcnow() if data.status == AdministrationStatus.GIVEN else None,
            administered_by=current_user.id,
            dose_given=data.dose_given,
            remarks=data.remarks,
            reason_not_given=data.reason_not_given
        )
        db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.get("/administer/{mar_id}", response_model=list[AdministrationResponse])
async def get_administrations(mar_id: int,
                               from_date: Optional[date] = Query(None),
                               db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    q = db.query(MedicationAdministration).filter(
        MedicationAdministration.mar_id == mar_id)
    if from_date:
        q = q.filter(MedicationAdministration.scheduled_datetime >= datetime.combine(from_date, datetime.min.time()))
    return q.order_by(MedicationAdministration.scheduled_datetime.desc()).all()


@router.get("/pending-doses/{admission_id}")
async def get_pending_doses(admission_id: int,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """Get all pending doses for today for an admission"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    mars = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.ipd_admission_id == admission_id,
        MedicationAdministrationRecord.is_active == True
    ).all()
    pending = []
    for mar in mars:
        admins = db.query(MedicationAdministration).filter(
            MedicationAdministration.mar_id == mar.id,
            MedicationAdministration.scheduled_datetime.between(today_start, today_end),
            MedicationAdministration.status == AdministrationStatus.SCHEDULED
        ).all()
        for a in admins:
            pending.append({
                "administration_id": a.id,
                "mar_id": mar.id,
                "drug_name": mar.drug_name,
                "dose": mar.dose,
                "route": mar.route,
                "scheduled_time": a.scheduled_datetime.strftime("%H:%M"),
                "instructions": mar.instructions,
                "status": a.status
            })
    return sorted(pending, key=lambda x: x["scheduled_time"])


# ── NURSING ASSESSMENTS ───────────────────────────────
@router.post("/assessments", response_model=NursingAssessmentResponse, status_code=201)
async def create_assessment(data: NursingAssessmentCreate,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    assessment = NursingAssessment(**data.model_dump(), assessed_by=current_user.id)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/assessments/{admission_id}", response_model=list[NursingAssessmentResponse])
async def get_assessments(admission_id: int,
                           assessment_type: Optional[str] = Query(None),
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    q = db.query(NursingAssessment).filter(
        NursingAssessment.ipd_admission_id == admission_id)
    if assessment_type:
        q = q.filter(NursingAssessment.assessment_type == assessment_type)
    return q.order_by(NursingAssessment.assessment_date.desc()).all()


# ── CARE PLANS ────────────────────────────────────────
@router.post("/care-plans", response_model=CarePlanResponse, status_code=201)
async def create_care_plan(data: CarePlanCreate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    plan = CarePlan(**data.model_dump(), created_by=current_user.id)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/care-plans/{admission_id}", response_model=list[CarePlanResponse])
async def get_care_plans(admission_id: int,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(CarePlan).filter(
        CarePlan.ipd_admission_id == admission_id
    ).order_by(CarePlan.created_at.desc()).all()


@router.put("/care-plans/{plan_id}", response_model=CarePlanResponse)
async def update_care_plan(plan_id: int, data: CarePlanUpdate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    plan = db.query(CarePlan).filter(CarePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/care-plans/{plan_id}/interventions")
async def add_intervention(plan_id: int, data: CareInterventionCreate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    plan = db.query(CarePlan).filter(CarePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    intervention = CareIntervention(
        care_plan_id=plan_id,
        intervention=data.intervention,
        outcome=data.outcome,
        patient_response=data.patient_response,
        performed_by=current_user.id
    )
    db.add(intervention)
    db.commit()
    return {"message": "Intervention recorded", "id": intervention.id}


# ── SHIFT HANDOVER ────────────────────────────────────
@router.post("/handover", response_model=ShiftHandoverResponse, status_code=201)
async def create_handover(data: ShiftHandoverCreate,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    handover = ShiftHandover(**data.model_dump(), handover_by=current_user.id)
    db.add(handover)
    db.commit()
    db.refresh(handover)
    return handover


@router.get("/handover", response_model=list[ShiftHandoverResponse])
async def list_handovers(ward_id: Optional[int] = Query(None),
                          shift_date: Optional[date] = Query(None),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(ShiftHandover)
    if ward_id:
        q = q.filter(ShiftHandover.ward_id == ward_id)
    if shift_date:
        q = q.filter(ShiftHandover.shift_date == shift_date)
    return q.order_by(ShiftHandover.created_at.desc()).limit(50).all()


@router.put("/handover/{handover_id}/receive")
async def receive_handover(handover_id: int,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    handover = db.query(ShiftHandover).filter(ShiftHandover.id == handover_id).first()
    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found")
    handover.received_by = current_user.id
    db.commit()
    return {"message": "Handover received", "received_by": current_user.id}


# ── DASHBOARD ─────────────────────────────────────────
@router.get("/dashboard/stats/{admission_id}")
async def nursing_dashboard(admission_id: int,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    active_mars = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.ipd_admission_id == admission_id,
        MedicationAdministrationRecord.is_active == True
    ).count()
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    pending_doses = db.query(MedicationAdministration).join(
        MedicationAdministrationRecord
    ).filter(
        MedicationAdministrationRecord.ipd_admission_id == admission_id,
        MedicationAdministration.scheduled_datetime.between(today_start, today_end),
        MedicationAdministration.status == AdministrationStatus.SCHEDULED
    ).count()
    active_care_plans = db.query(CarePlan).filter(
        CarePlan.ipd_admission_id == admission_id,
        CarePlan.status == "active"
    ).count()
    last_assessment = db.query(NursingAssessment).filter(
        NursingAssessment.ipd_admission_id == admission_id
    ).order_by(NursingAssessment.assessment_date.desc()).first()
    return {
        "active_medications": active_mars,
        "pending_doses_today": pending_doses,
        "active_care_plans": active_care_plans,
        "last_assessment": last_assessment.assessment_date if last_assessment else None,
        "last_assessment_type": last_assessment.assessment_type if last_assessment else None
    }


