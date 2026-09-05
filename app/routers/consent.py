from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.consent import ConsentTemplate, PatientConsent, ConsentStatus
from app.models.user import User
from app.schemas.consent import (
    ConsentTemplateCreate, ConsentTemplateResponse,
    PatientConsentCreate, PatientConsentSign, PatientConsentWithdraw, PatientConsentResponse,
)

router = APIRouter(prefix="/consent", tags=["Consent Management"])


# ── TEMPLATES ─────────────────────────────────────────
@router.post("/templates", response_model=ConsentTemplateResponse, status_code=201)
async def create_template(data: ConsentTemplateCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    template = ConsentTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates", response_model=List[ConsentTemplateResponse])
async def list_templates(category: Optional[str] = None, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(ConsentTemplate).filter(ConsentTemplate.is_active == True)
    if category:
        q = q.filter(ConsentTemplate.category == category)
    return q.all()


# ── PATIENT CONSENTS ───────────────────────────────────
@router.post("/patient-consents", response_model=PatientConsentResponse, status_code=201)
async def create_patient_consent(data: PatientConsentCreate, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    """Raise a pending consent for a patient to review/sign (e.g. before surgery/anesthesia)."""
    template = db.query(ConsentTemplate).filter(ConsentTemplate.id == data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Consent template not found")
    consent = PatientConsent(**data.model_dump())
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


@router.get("/patient-consents", response_model=List[PatientConsentResponse])
async def list_patient_consents(patient_id: Optional[int] = None, status: Optional[ConsentStatus] = None,
                                 source: Optional[str] = None, source_id: Optional[int] = None,
                                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(PatientConsent)
    if patient_id:
        q = q.filter(PatientConsent.patient_id == patient_id)
    if status:
        q = q.filter(PatientConsent.status == status)
    if source:
        q = q.filter(PatientConsent.source == source)
    if source_id:
        q = q.filter(PatientConsent.source_id == source_id)
    return q.order_by(PatientConsent.created_at.desc()).all()


@router.post("/patient-consents/{consent_id}/sign", response_model=PatientConsentResponse)
async def sign_consent(consent_id: int, data: PatientConsentSign, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    consent = db.query(PatientConsent).filter(PatientConsent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    if consent.status == ConsentStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Consent already signed")

    template = db.query(ConsentTemplate).filter(ConsentTemplate.id == consent.template_id).first()
    if template and template.requires_witness and not data.witness_name:
        raise HTTPException(status_code=400, detail="This consent requires a witness name")

    consent.consented_by_name = data.consented_by_name
    consent.relationship_to_patient = data.relationship_to_patient
    consent.signature_data = data.signature_data
    consent.witness_name = data.witness_name
    consent.status = ConsentStatus.SIGNED
    consent.signed_at = datetime.now(timezone.utc)
    if template and template.validity_days:
        consent.expires_at = consent.signed_at + timedelta(days=template.validity_days)

    db.commit()
    db.refresh(consent)
    return consent


@router.post("/patient-consents/{consent_id}/refuse", response_model=PatientConsentResponse)
async def refuse_consent(consent_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    consent = db.query(PatientConsent).filter(PatientConsent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    consent.status = ConsentStatus.REFUSED
    db.commit()
    db.refresh(consent)
    return consent


@router.post("/patient-consents/{consent_id}/withdraw", response_model=PatientConsentResponse)
async def withdraw_consent(consent_id: int, data: PatientConsentWithdraw, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    consent = db.query(PatientConsent).filter(PatientConsent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    if consent.status != ConsentStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Only a signed consent can be withdrawn")
    consent.status = ConsentStatus.WITHDRAWN
    consent.withdrawn_at = datetime.now(timezone.utc)
    consent.withdrawal_reason = data.withdrawal_reason
    db.commit()
    db.refresh(consent)
    return consent
