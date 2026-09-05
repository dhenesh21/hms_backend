from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.family import FamilyMember
from app.models.appointment import Appointment, AppointmentStatus
from app.models.ipd import IPDAdmission, IPDStatus
from app.models.user import User
from app.schemas.family import FamilyMemberCreate, FamilyMemberResponse, FamilyHealthSummary

router = APIRouter(prefix="/family", tags=["Family / Proxy / Caregiver"])


@router.post("/members", response_model=FamilyMemberResponse, status_code=201)
async def add_family_member(data: FamilyMemberCreate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    if not data.linked_patient_id and not data.name:
        raise HTTPException(status_code=400, detail="Provide either linked_patient_id or a name")
    member = FamilyMember(**data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/members/patient/{patient_id}", response_model=List[FamilyMemberResponse])
async def list_family_members(patient_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    return db.query(FamilyMember).filter(FamilyMember.patient_id == patient_id).all()


@router.delete("/members/{member_id}", status_code=204)
async def remove_family_member(member_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    db.delete(member)
    db.commit()


# ── FAMILY HEALTH (item 196) ────────────────────────────
@router.get("/health-summary/patient/{patient_id}", response_model=List[FamilyHealthSummary])
async def family_health_summary(patient_id: int, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    """
    Coarse status only (upcoming appointment? currently admitted?) for family
    members who are themselves registered patients — not their clinical records.
    A linked family member seeing their own detail still goes through their own
    Patient Portal login; this view exists so one family member (e.g. a parent
    managing a household) can see who needs attention without seeing why.
    """
    members = db.query(FamilyMember).filter(
        FamilyMember.patient_id == patient_id, FamilyMember.linked_patient_id.isnot(None)
    ).all()

    summaries = []
    for m in members:
        has_upcoming = db.query(Appointment).filter(
            Appointment.patient_id == m.linked_patient_id,
            Appointment.appointment_date >= date.today(),
            Appointment.status == AppointmentStatus.SCHEDULED,
        ).first() is not None
        has_active_ipd = db.query(IPDAdmission).filter(
            IPDAdmission.patient_id == m.linked_patient_id,
            IPDAdmission.status == IPDStatus.ADMITTED,
        ).first() is not None
        summaries.append(FamilyHealthSummary(
            linked_patient_id=m.linked_patient_id, relation_type=m.relation_type,
            has_upcoming_appointment=has_upcoming, has_active_ipd_admission=has_active_ipd,
        ))
    return summaries
