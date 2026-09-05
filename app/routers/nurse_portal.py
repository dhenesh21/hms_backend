from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone, date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.ipd import IPDAdmission, IPDStatus, NursingNote
from app.models.nursing import (MedicationAdministrationRecord, MedicationAdministration,
                                 AdministrationStatus, ShiftHandover, CarePlan)
from app.models.nurse_roster import NurseWardAssignment
from app.schemas.nurse_portal import (
    WardPatientResponse, DueMedicationResponse, GiveMedicationRequest, MarkNotGivenRequest,
    LatestHandoverResponse, NursingCarePlanResponse, NursingNoteCreate, NursingNoteResponse,
)

router = APIRouter(prefix="/nurse-portal", tags=["Nurse Portal"])


def _require_nurse(current_user: User):
    if current_user.role != UserRole.NURSE:
        raise HTTPException(status_code=403, detail="Nurse portal is for nurse accounts only")


# A NurseWardAssignment roster now exists (models/nurse_roster.py). The endpoints
# below still take ward_id as an explicit parameter — that stays useful for a
# charge nurse or float pool covering multiple wards — but /my-wards below is the
# roster-scoped one: it resolves "my ward" from today's actual assignment instead
# of trusting whatever ward_id the client passes.

@router.get("/my-wards", response_model=List[int])
async def my_assigned_wards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Ward IDs this nurse is actually rostered on today — use this to build the
    ward picker instead of letting the client type in an arbitrary ward_id."""
    _require_nurse(current_user)
    rows = db.query(NurseWardAssignment.ward_id).filter(
        NurseWardAssignment.nurse_id == current_user.id,
        NurseWardAssignment.assignment_date == date.today(),
    ).distinct().all()
    return [r[0] for r in rows]


@router.get("/ward/{ward_id}/patients", response_model=List[WardPatientResponse])

async def ward_patients(ward_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    admissions = db.query(IPDAdmission).filter(
        IPDAdmission.ward_id == ward_id, IPDAdmission.status == IPDStatus.ADMITTED
    ).all()
    return [
        WardPatientResponse(admission_id=a.id, patient_id=a.patient_id, bed_id=a.bed_id,
                             admission_date=a.admission_date, status=a.status.value)
        for a in admissions
    ]


@router.get("/due-medications", response_model=List[DueMedicationResponse])
async def due_medications(window_minutes: int = 60, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Scheduled doses due in the next `window_minutes` — the core MAR worklist."""
    _require_nurse(current_user)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(minutes=window_minutes)

    rows = (
        db.query(MedicationAdministration, MedicationAdministrationRecord)
        .join(MedicationAdministrationRecord,
              MedicationAdministration.mar_id == MedicationAdministrationRecord.id)
        .filter(
            MedicationAdministration.status == AdministrationStatus.SCHEDULED,
            MedicationAdministration.scheduled_datetime <= horizon,
            MedicationAdministrationRecord.is_active == True,
        )
        .order_by(MedicationAdministration.scheduled_datetime)
        .all()
    )
    return [
        DueMedicationResponse(
            administration_id=admin.id, mar_id=mar.id, patient_id=mar.patient_id,
            drug_name=mar.drug_name, dose=mar.dose, route=mar.route,
            scheduled_datetime=admin.scheduled_datetime, status=admin.status.value,
        )
        for admin, mar in rows
    ]


@router.post("/due-medications/{administration_id}/give", response_model=DueMedicationResponse)
async def give_medication(administration_id: int, data: GiveMedicationRequest, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    admin = db.query(MedicationAdministration).filter(MedicationAdministration.id == administration_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Scheduled dose not found")
    mar = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.id == admin.mar_id).first()

    admin.status = AdministrationStatus.GIVEN
    admin.administered_datetime = datetime.now(timezone.utc)
    admin.administered_by = current_user.id
    admin.dose_given = data.dose_given or mar.dose
    admin.remarks = data.remarks
    db.commit()
    db.refresh(admin)
    return DueMedicationResponse(
        administration_id=admin.id, mar_id=mar.id, patient_id=mar.patient_id,
        drug_name=mar.drug_name, dose=mar.dose, route=mar.route,
        scheduled_datetime=admin.scheduled_datetime, status=admin.status.value,
    )


@router.post("/due-medications/{administration_id}/not-given", response_model=DueMedicationResponse)
async def mark_not_given(administration_id: int, data: MarkNotGivenRequest, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    admin = db.query(MedicationAdministration).filter(MedicationAdministration.id == administration_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Scheduled dose not found")
    mar = db.query(MedicationAdministrationRecord).filter(
        MedicationAdministrationRecord.id == admin.mar_id).first()

    try:
        admin.status = AdministrationStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="status must be one of: held, missed, refused")
    admin.reason_not_given = data.reason_not_given
    admin.administered_by = current_user.id
    db.commit()
    db.refresh(admin)
    return DueMedicationResponse(
        administration_id=admin.id, mar_id=mar.id, patient_id=mar.patient_id,
        drug_name=mar.drug_name, dose=mar.dose, route=mar.route,
        scheduled_datetime=admin.scheduled_datetime, status=admin.status.value,
    )


@router.get("/ward/{ward_id}/handover/latest", response_model=LatestHandoverResponse)
async def latest_handover(ward_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    handover = db.query(ShiftHandover).filter(ShiftHandover.ward_id == ward_id).order_by(
        ShiftHandover.shift_date.desc(), ShiftHandover.created_at.desc()
    ).first()
    if not handover:
        raise HTTPException(status_code=404, detail="No handover recorded for this ward yet")
    return handover


@router.get("/care-plans/patient/{patient_id}", response_model=List[NursingCarePlanResponse])
async def nursing_care_plans(patient_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    plans = db.query(CarePlan).filter(CarePlan.patient_id == patient_id).all()
    return [
        NursingCarePlanResponse(id=p.id, patient_id=p.patient_id, problem_statement=p.problem_statement,
                                 goal=p.goal, status=p.status.value, priority=p.priority)
        for p in plans
    ]


@router.post("/notes", response_model=NursingNoteResponse, status_code=201)
async def add_nursing_note(data: NursingNoteCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    note = NursingNote(**data.model_dump(), nurse_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes/admission/{admission_id}", response_model=List[NursingNoteResponse])
async def list_notes(admission_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _require_nurse(current_user)
    return db.query(NursingNote).filter(
        NursingNote.admission_id == admission_id
    ).order_by(NursingNote.created_at.desc()).all()
