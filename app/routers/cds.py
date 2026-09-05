from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.cds import CDSRule, CDSAlertLog
from app.models.user import User
from app.schemas.cds import CDSRuleCreate, CDSRuleResponse, CDSAlertResponse, CDSOverrideRequest

router = APIRouter(prefix="/cds", tags=["Clinical Decision Support"])


@router.post("/rules", response_model=CDSRuleResponse, status_code=201)
async def create_rule(data: CDSRuleCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    rule = CDSRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/rules", response_model=List[CDSRuleResponse])
async def list_rules(active_only: bool = True, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    q = db.query(CDSRule)
    if active_only:
        q = q.filter(CDSRule.is_active == True)
    return q.all()


@router.delete("/rules/{rule_id}", status_code=204)
async def deactivate_rule(rule_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    rule = db.query(CDSRule).filter(CDSRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.is_active = False
    db.commit()


@router.get("/alerts/patient/{patient_id}", response_model=List[CDSAlertResponse])
async def get_patient_alerts(patient_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return db.query(CDSAlertLog).filter(
        CDSAlertLog.patient_id == patient_id
    ).order_by(CDSAlertLog.created_at.desc()).all()


@router.post("/alerts/{alert_id}/override", response_model=CDSAlertResponse)
async def override_alert(alert_id: int, data: CDSOverrideRequest, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Doctor explicitly overrides a CDS warning to proceed anyway — logged for audit."""
    alert = db.query(CDSAlertLog).filter(CDSAlertLog.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.was_overridden = True
    alert.override_reason = data.override_reason
    alert.overridden_by = current_user.id
    db.commit()
    db.refresh(alert)
    return alert
