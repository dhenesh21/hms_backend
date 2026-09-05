from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.data_exchange import DataExchangeAuthorization, DataExchangeLog, ExchangeAuthStatus, DataCategory
from app.models.user import User
from app.schemas.data_exchange import (
    ExchangeAuthCreate, ExchangeAuthRevoke, ExchangeAuthResponse,
    ExchangeLogCreate, ExchangeLogResponse, ExchangeCheckResult,
)

router = APIRouter(prefix="/data-exchange", tags=["Consent-based Data Exchange"])


@router.post("/authorizations", response_model=ExchangeAuthResponse, status_code=201)
async def grant_authorization(data: ExchangeAuthCreate, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    if not data.authorized_facility_id and not data.authorized_provider_id and not data.authorized_party_name_freetext:
        raise HTTPException(status_code=400, detail="Specify a facility, provider, or at least a party name")
    auth = DataExchangeAuthorization(**data.model_dump())
    db.add(auth)
    db.commit()
    db.refresh(auth)
    return auth


@router.get("/authorizations/patient/{patient_id}", response_model=List[ExchangeAuthResponse])
async def list_authorizations(patient_id: int, active_only: bool = True, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    q = db.query(DataExchangeAuthorization).filter(DataExchangeAuthorization.patient_id == patient_id)
    if active_only:
        q = q.filter(DataExchangeAuthorization.status == ExchangeAuthStatus.ACTIVE)
    return q.all()


@router.post("/authorizations/{auth_id}/revoke", response_model=ExchangeAuthResponse)
async def revoke_authorization(auth_id: int, data: ExchangeAuthRevoke, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    auth = db.query(DataExchangeAuthorization).filter(DataExchangeAuthorization.id == auth_id).first()
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    auth.status = ExchangeAuthStatus.REVOKED
    auth.revoked_at = datetime.now(timezone.utc)
    auth.revoked_reason = data.revoked_reason
    db.commit()
    db.refresh(auth)
    return auth


@router.get("/check", response_model=ExchangeCheckResult)
async def check_authorization(patient_id: int, data_category: DataCategory, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """
    Whether an active, non-expired authorization exists covering this
    patient + data category — call this before releasing data to an
    external party through any channel (not just FHIR/HL7). Returns a
    reason either way so a caller can log/display why access was or wasn't
    granted, rather than a bare boolean.
    """
    now = datetime.now(timezone.utc)
    auths = db.query(DataExchangeAuthorization).filter(
        DataExchangeAuthorization.patient_id == patient_id,
        DataExchangeAuthorization.status == ExchangeAuthStatus.ACTIVE,
    ).all()
    for a in auths:
        if a.expires_at and a.expires_at < now:
            continue
        categories = a.data_categories or []
        if data_category.value in categories or DataCategory.FULL_RECORD.value in categories:
            return ExchangeCheckResult(authorized=True, matching_authorization_id=a.id)
    return ExchangeCheckResult(authorized=False, reason="No active authorization covers this patient and data category")


@router.post("/logs", response_model=ExchangeLogResponse, status_code=201)
async def log_exchange(data: ExchangeLogCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    log = DataExchangeLog(**data.model_dump(), accessed_by_user_id=current_user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/logs/authorization/{auth_id}", response_model=List[ExchangeLogResponse])
async def list_logs(auth_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DataExchangeLog).filter(
        DataExchangeLog.authorization_id == auth_id
    ).order_by(DataExchangeLog.created_at.desc()).all()
