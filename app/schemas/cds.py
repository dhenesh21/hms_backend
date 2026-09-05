from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.cds import CDSRuleType, CDSSeverity


class CDSRuleCreate(BaseModel):
    rule_name: str
    rule_type: CDSRuleType
    severity: CDSSeverity = CDSSeverity.WARNING
    trigger_keyword: str
    conflict_keyword: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    message: str


class CDSRuleResponse(BaseModel):
    id: int
    rule_name: str
    rule_type: CDSRuleType
    severity: CDSSeverity
    trigger_keyword: str
    conflict_keyword: Optional[str]
    message: str
    is_active: bool

    class Config:
        from_attributes = True


class CDSAlertResponse(BaseModel):
    id: int
    rule_id: Optional[int]
    patient_id: int
    clinical_order_id: Optional[int]
    severity: CDSSeverity
    message: str
    was_overridden: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CDSOverrideRequest(BaseModel):
    override_reason: str
