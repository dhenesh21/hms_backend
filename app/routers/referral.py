from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.referral import Referral, ReferralStatus, ReferralType
from app.models.patient import Patient

router = APIRouter(tags=["Referrals"])


@router.post("/referrals", status_code=201)
async def create_referral(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Referral).count()
    ref = Referral(
        referral_number=f"REF{count+1:05d}",
        patient_id=data["patient_id"],
        referring_doctor_id=data.get("referring_doctor_id", current_user.id),
        referred_to_doctor_id=data.get("referred_to_doctor_id"),
        referred_to_hospital=data.get("referred_to_hospital"),
        referred_to_department=data.get("referred_to_department"),
        referral_type=data.get("referral_type", "internal"),
        reason=data["reason"],
        clinical_summary=data.get("clinical_summary"),
        urgency=data.get("urgency", "routine"),
        appointment_date=data.get("appointment_date"),
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "referral_number": ref.referral_number}


@router.get("/referrals")
async def list_referrals(
    status: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Referral).filter(Referral.is_active == True)
    if status:
        q = q.filter(Referral.status == status)
    if patient_id:
        q = q.filter(Referral.patient_id == patient_id)
    referrals = q.order_by(Referral.created_at.desc()).limit(100).all()

    result = []
    for r in referrals:
        patient = db.query(Patient).filter(Patient.id == r.patient_id).first()
        ref_doc = db.query(User).filter(User.id == r.referring_doctor_id).first()
        to_doc = db.query(User).filter(User.id == r.referred_to_doctor_id).first() if r.referred_to_doctor_id else None
        result.append({
            "id": r.id, "referral_number": r.referral_number,
            "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "—",
            "patient_uhid": patient.uhid if patient else "—",
            "referring_doctor": ref_doc.full_name if ref_doc else "—",
            "referred_to_doctor": to_doc.full_name if to_doc else None,
            "referred_to_hospital": r.referred_to_hospital,
            "referred_to_department": r.referred_to_department,
            "referral_type": r.referral_type,
            "reason": r.reason, "urgency": r.urgency,
            "status": r.status, "referral_date": r.referral_date,
            "appointment_date": r.appointment_date,
        })
    return result


@router.put("/referrals/{referral_id}/status")
async def update_referral_status(
    referral_id: int, data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    ref.status = data.get("status", ref.status)
    ref.notes = data.get("notes", ref.notes)
    db.commit()
    return {"message": "Updated"}


@router.get("/referrals/{referral_id}/print")
async def get_referral_print_data(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Not found")
    patient = db.query(Patient).filter(Patient.id == ref.patient_id).first()
    ref_doc = db.query(User).filter(User.id == ref.referring_doctor_id).first()
    to_doc = db.query(User).filter(User.id == ref.referred_to_doctor_id).first() if ref.referred_to_doctor_id else None
    return {
        "referral_number": ref.referral_number,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "—",
        "patient_uhid": patient.uhid if patient else "—",
        "patient_age": patient.date_of_birth.strftime("%Y") if patient and patient.date_of_birth else "—",
        "patient_gender": patient.gender if patient else "—",
        "patient_phone": patient.phone if patient else "—",
        "referring_doctor": ref_doc.full_name if ref_doc else "—",
        "referred_to_doctor": to_doc.full_name if to_doc else None,
        "referred_to_hospital": ref.referred_to_hospital,
        "referred_to_department": ref.referred_to_department,
        "referral_type": ref.referral_type,
        "reason": ref.reason,
        "clinical_summary": ref.clinical_summary,
        "urgency": ref.urgency,
        "referral_date": str(ref.referral_date.date()) if ref.referral_date else "—",
        "appointment_date": str(ref.appointment_date) if ref.appointment_date else None,
    }
