from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import get_current_user, get_current_patient
from app.models.telemedicine import VirtualConsultation, ConsultationStatus
from app.models.patient_portal import PatientAccount
from app.models.user import User
from app.schemas.telemedicine import (
    VirtualConsultCreate, VirtualConsultUpdate, VirtualConsultComplete,
    VirtualConsultCancel, VirtualConsultResponse,
)

router = APIRouter(prefix="/telemedicine", tags=["Telemedicine / Virtual Consultation"])


@router.get("/my-consultations", response_model=List[VirtualConsultResponse])
async def my_consultations(status: Optional[ConsultationStatus] = None, db: Session = Depends(get_db),
                            account: PatientAccount = Depends(get_current_patient)):
    """
    Patient-facing equivalent of GET /consultations — that endpoint requires
    staff auth (get_current_user), which explicitly rejects patient-scoped
    tokens by design (see core/security.py). This is the one the Patient
    Portal / mobile app calls instead, auto-scoped to the caller's own
    patient_id so a patient can never pass another patient_id and see someone
    else's consultations.
    """
    q = db.query(VirtualConsultation).filter(VirtualConsultation.patient_id == account.patient_id)
    if status:
        q = q.filter(VirtualConsultation.status == status)
    return q.order_by(VirtualConsultation.scheduled_at.desc()).all()


@router.post("/consultations", response_model=VirtualConsultResponse, status_code=201)
async def schedule_consultation(data: VirtualConsultCreate, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    payload = data.model_dump()

    # Item 188-190 — a real, working video vendor with zero setup: Jitsi
    # Meet's public server needs no account, no API key, no contract — a
    # unique room URL just works the moment two people open it. This is the
    # sane zero-cost default so consultations are actually joinable out of
    # the box; meeting-details can still be overridden below (PATCH
    # /consultations/{id}/meeting-details) if the hospital later picks a
    # paid vendor (Twilio/Agora/Daily) for recording, waiting rooms, EHR
    # embedding, etc. Self-hosting Jitsi is the recommended step up before
    # relying on this for real patient volume — meet.jit.si is a shared
    # public instance with no uptime/capacity guarantee, fine for getting
    # telemedicine actually working today, not a permanent production
    # commitment.
    if not payload.get("meeting_link"):
        room_id = f"HMS-{uuid.uuid4().hex[:12]}"
        payload["meeting_link"] = f"https://meet.jit.si/{room_id}"
        payload["meeting_provider"] = "jitsi"
        payload["meeting_id_external"] = room_id

    consult = VirtualConsultation(**payload)
    db.add(consult)
    db.commit()
    db.refresh(consult)
    return consult


@router.get("/consultations", response_model=List[VirtualConsultResponse])
async def list_consultations(patient_id: Optional[int] = None, doctor_id: Optional[int] = None,
                              status: Optional[ConsultationStatus] = None, is_second_opinion: Optional[bool] = None,
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(VirtualConsultation)
    if patient_id:
        q = q.filter(VirtualConsultation.patient_id == patient_id)
    if doctor_id:
        q = q.filter(VirtualConsultation.doctor_id == doctor_id)
    if status:
        q = q.filter(VirtualConsultation.status == status)
    if is_second_opinion is not None:
        q = q.filter(VirtualConsultation.is_second_opinion == is_second_opinion)
    return q.order_by(VirtualConsultation.scheduled_at.desc()).all()


@router.patch("/consultations/{consult_id}/meeting-details", response_model=VirtualConsultResponse)
async def set_meeting_details(consult_id: int, data: VirtualConsultUpdate, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """Populate the meeting link once the chosen video vendor session is created."""
    consult = db.query(VirtualConsultation).filter(VirtualConsultation.id == consult_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(consult, k, v)
    db.commit()
    db.refresh(consult)
    return consult


@router.post("/consultations/{consult_id}/start", response_model=VirtualConsultResponse)
async def start_consultation(consult_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    consult = db.query(VirtualConsultation).filter(VirtualConsultation.id == consult_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consult.status = ConsultationStatus.IN_PROGRESS
    consult.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consult)
    return consult


@router.post("/consultations/{consult_id}/complete", response_model=VirtualConsultResponse)
async def complete_consultation(consult_id: int, data: VirtualConsultComplete, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    consult = db.query(VirtualConsultation).filter(VirtualConsultation.id == consult_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consult.consultation_notes = data.consultation_notes
    consult.prescription_issued = data.prescription_issued
    consult.follow_up_advised = data.follow_up_advised
    consult.status = ConsultationStatus.COMPLETED
    consult.ended_at = datetime.now(timezone.utc)
    if consult.started_at:
        consult.duration_minutes = int((consult.ended_at - consult.started_at).total_seconds() // 60)
    db.commit()
    db.refresh(consult)
    return consult


@router.post("/consultations/{consult_id}/cancel", response_model=VirtualConsultResponse)
async def cancel_consultation(consult_id: int, data: VirtualConsultCancel, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    consult = db.query(VirtualConsultation).filter(VirtualConsultation.id == consult_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consult.status = ConsultationStatus.CANCELLED
    consult.cancellation_reason = data.cancellation_reason
    db.commit()
    db.refresh(consult)
    return consult


@router.post("/consultations/{consult_id}/no-show", response_model=VirtualConsultResponse)
async def mark_no_show(consult_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    consult = db.query(VirtualConsultation).filter(VirtualConsultation.id == consult_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    consult.status = ConsultationStatus.NO_SHOW
    db.commit()
    db.refresh(consult)
    return consult
