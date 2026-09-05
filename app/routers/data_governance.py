from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.data_governance import (DataAssetRegistry, RetentionPolicy, ArchivalJob,
                                         DataQualityRule, DataQualityFinding)
from app.models.user import User
from app.schemas.data_governance import (
    DataAssetCreate, DataAssetResponse,
    RetentionPolicyCreate, RetentionPolicyResponse,
    ArchivalJobCreate, ArchivalJobResponse,
    DQRuleCreate, DQRuleResponse,
    DQFindingCreate, DQFindingResolve, DQFindingResponse,
)

router = APIRouter(prefix="/data-governance", tags=["Data Governance"])


# ── DATA ASSET REGISTRY (item 242) ─────────────────────
@router.post("/assets", response_model=DataAssetResponse, status_code=201)
async def register_asset(data: DataAssetCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    existing = db.query(DataAssetRegistry).filter(DataAssetRegistry.table_name == data.table_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="This table is already registered")
    asset = DataAssetRegistry(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/assets", response_model=List[DataAssetResponse])
async def list_assets(domain: Optional[str] = None, contains_phi: Optional[bool] = None,
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(DataAssetRegistry)
    if domain:
        q = q.filter(DataAssetRegistry.domain == domain)
    if contains_phi is not None:
        q = q.filter(DataAssetRegistry.contains_phi == contains_phi)
    return q.all()


# ── RETENTION POLICY (item 243) ────────────────────────
@router.post("/retention-policies", response_model=RetentionPolicyResponse, status_code=201)
async def create_policy(data: RetentionPolicyCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    policy = RetentionPolicy(**data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/retention-policies", response_model=List[RetentionPolicyResponse])
async def list_policies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(RetentionPolicy).filter(RetentionPolicy.is_active == True).all()


# ── ARCHIVAL JOBS (item 244) ───────────────────────────
@router.post("/archival-jobs", response_model=ArchivalJobResponse, status_code=201)
async def log_archival_job(data: ArchivalJobCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    job = ArchivalJob(**data.model_dump(), triggered_by=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/archival-jobs", response_model=List[ArchivalJobResponse])
async def list_archival_jobs(data_asset_id: Optional[int] = None, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    q = db.query(ArchivalJob)
    if data_asset_id:
        q = q.filter(ArchivalJob.data_asset_id == data_asset_id)
    return q.order_by(ArchivalJob.created_at.desc()).all()


# ── DATA QUALITY (item 241) ────────────────────────────
@router.post("/quality-rules", response_model=DQRuleResponse, status_code=201)
async def create_rule(data: DQRuleCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    rule = DataQualityRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/quality-rules", response_model=List[DQRuleResponse])
async def list_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DataQualityRule).filter(DataQualityRule.is_active == True).all()


@router.post("/quality-findings", response_model=DQFindingResponse, status_code=201)
async def log_finding(data: DQFindingCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    finding = DataQualityFinding(**data.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.get("/quality-findings", response_model=List[DQFindingResponse])
async def list_findings(resolved: Optional[bool] = False, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(DataQualityFinding)
    if resolved is not None:
        q = q.filter(DataQualityFinding.resolved == resolved)
    return q.order_by(DataQualityFinding.created_at.desc()).all()


@router.post("/quality-findings/{finding_id}/resolve", response_model=DQFindingResponse)
async def resolve_finding(finding_id: int, data: DQFindingResolve, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    finding = db.query(DataQualityFinding).filter(DataQualityFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.resolved = True
    finding.resolved_by = current_user.id
    finding.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(finding)
    return finding
