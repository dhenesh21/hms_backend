from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from app.models.data_governance import DataClassification, RetentionAction


class DataAssetCreate(BaseModel):
    table_name: str
    domain: Optional[str] = None
    classification: DataClassification = DataClassification.INTERNAL
    contains_phi: bool = False
    business_owner: Optional[str] = None
    description: Optional[str] = None


class DataAssetResponse(BaseModel):
    id: int
    table_name: str
    domain: Optional[str]
    classification: DataClassification
    contains_phi: bool
    business_owner: Optional[str]

    class Config:
        from_attributes = True


class RetentionPolicyCreate(BaseModel):
    data_asset_id: int
    retain_for_years: int
    action_after_retention: RetentionAction = RetentionAction.ARCHIVE
    legal_basis: Optional[str] = None


class RetentionPolicyResponse(BaseModel):
    id: int
    data_asset_id: int
    retain_for_years: int
    action_after_retention: RetentionAction
    legal_basis: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class ArchivalJobCreate(BaseModel):
    data_asset_id: int
    cutoff_date: date
    records_affected: Optional[int] = None
    notes: Optional[str] = None


class ArchivalJobResponse(BaseModel):
    id: int
    data_asset_id: int
    cutoff_date: date
    records_affected: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DQRuleCreate(BaseModel):
    rule_name: str
    data_asset_id: Optional[int] = None
    rule_type: str
    check_description: str
    severity: str = "warning"


class DQRuleResponse(BaseModel):
    id: int
    rule_name: str
    rule_type: str
    check_description: str
    severity: str
    is_active: bool

    class Config:
        from_attributes = True


class DQFindingCreate(BaseModel):
    rule_id: int
    affected_table: Optional[str] = None
    affected_record_id: Optional[int] = None
    finding_details: Optional[dict] = None


class DQFindingResolve(BaseModel):
    notes: Optional[str] = None


class DQFindingResponse(BaseModel):
    id: int
    rule_id: int
    affected_table: Optional[str]
    affected_record_id: Optional[int]
    finding_details: Any
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True
