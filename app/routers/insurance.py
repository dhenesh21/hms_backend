from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.insurance import (InsuranceCompany, InsurancePolicy,
                                   InsuranceClaim, ClaimDocument, ClaimStatus)
from app.models.user import User
from app.schemas.insurance import (
    InsuranceCompanyCreate, InsuranceCompanyResponse,
    PolicyCreate, PolicyResponse,
    ClaimCreate, ClaimUpdate, ClaimResponse,
    PreAuthRequest, ClaimDocumentCreate, ClaimDocumentResponse
)

router = APIRouter(prefix="/insurance", tags=["Insurance / TPA"])


# ── INSURANCE COMPANIES ───────────────────────────────
@router.post("/companies", response_model=InsuranceCompanyResponse, status_code=201)
async def create_company(data: InsuranceCompanyCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    co = InsuranceCompany(**data.model_dump())
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


@router.get("/companies", response_model=list[InsuranceCompanyResponse])
async def list_companies(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(InsuranceCompany).filter(InsuranceCompany.is_active == True).all()


# ── POLICIES ──────────────────────────────────────────
@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(data: PolicyCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    if db.query(InsurancePolicy).filter(InsurancePolicy.policy_number == data.policy_number).first():
        raise HTTPException(status_code=400, detail="Policy number already exists")
    policy = InsurancePolicy(**data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(patient_id: Optional[int] = Query(None),
                         active_only: bool = Query(True),
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(InsurancePolicy)
    if patient_id:
        q = q.filter(InsurancePolicy.patient_id == patient_id)
    if active_only:
        q = q.filter(InsurancePolicy.is_active == True)
    return q.all()


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    p = db.query(InsurancePolicy).filter(InsurancePolicy.id == policy_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    return p


# ── CLAIMS ────────────────────────────────────────────
@router.post("/claims", response_model=ClaimResponse, status_code=201)
async def create_claim(data: ClaimCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    from sqlalchemy.exc import IntegrityError

    claim_data = data.model_dump()
    claim_data["created_by"] = current_user.id

    attempt_base = next_sequence_number(db, InsuranceClaim)
    claim = None
    last_error = None
    for i in range(MAX_RETRIES):
        claim_data["claim_number"] = f"CLM{datetime.now().year}{attempt_base + i:06d}"
        claim = InsuranceClaim(**claim_data)
        db.add(claim)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            claim = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(claim)
    return claim


@router.get("/claims", response_model=list[ClaimResponse])
async def list_claims(patient_id: Optional[int] = Query(None),
                       status: Optional[ClaimStatus] = Query(None),
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    q = db.query(InsuranceClaim)
    if patient_id:
        q = q.filter(InsuranceClaim.patient_id == patient_id)
    if status:
        q = q.filter(InsuranceClaim.status == status)
    return q.order_by(InsuranceClaim.created_at.desc()).limit(100).all()


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    c = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    return c


@router.put("/claims/{claim_id}", response_model=ClaimResponse)
async def update_claim(claim_id: int, data: ClaimUpdate,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(claim, field, value)
    if data.status == ClaimStatus.SUBMITTED:
        claim.submitted_at = datetime.utcnow()
    if data.status == ClaimStatus.SETTLED:
        claim.settled_at = datetime.utcnow()
    if data.status == ClaimStatus.APPEALED:
        claim.appealed_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)
    return claim


# ── PRE-AUTHORIZATION ─────────────────────────────────
@router.post("/claims/{claim_id}/request-preauth")
async def request_preauth(claim_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.status = ClaimStatus.PREAUTH_REQUESTED
    claim.preauth_requested_at = datetime.utcnow()
    db.commit()
    return {"message": "Pre-authorization requested", "claim_number": claim.claim_number}


@router.post("/claims/{claim_id}/preauth-response")
async def preauth_response(claim_id: int, data: PreAuthRequest,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.preauth_number = data.preauth_number
    claim.preauth_notes = data.preauth_notes
    if data.approved:
        claim.status = ClaimStatus.PREAUTH_APPROVED
        claim.preauth_approved_at = datetime.utcnow()
        claim.preauth_approved_amount = data.preauth_approved_amount
        claim.preauth_validity_date = data.preauth_validity_date
    else:
        claim.status = ClaimStatus.PREAUTH_REJECTED
    db.commit()
    db.refresh(claim)
    return claim


# ── SUBMIT CLAIM ──────────────────────────────────────
@router.post("/claims/{claim_id}/submit")
async def submit_claim(claim_id: int, submission_reference: Optional[str] = None,
                        documents: Optional[list] = None,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.status = ClaimStatus.SUBMITTED
    claim.submitted_at = datetime.utcnow()
    claim.submission_reference = submission_reference
    if documents:
        claim.documents_submitted = documents
    db.commit()
    return {"message": "Claim submitted", "claim_number": claim.claim_number,
            "submitted_at": claim.submitted_at}


# ── DOCUMENTS ─────────────────────────────────────────
@router.post("/claims/{claim_id}/documents", response_model=ClaimDocumentResponse, status_code=201)
async def add_document(claim_id: int, data: ClaimDocumentCreate,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    doc = ClaimDocument(**data.model_dump(), uploaded_by=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/claims/{claim_id}/documents", response_model=list[ClaimDocumentResponse])
async def get_documents(claim_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim_id).all()


# ── DASHBOARD ─────────────────────────────────────────
@router.get("/dashboard/stats")
async def insurance_stats(db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    total = db.query(InsuranceClaim).count()
    preauth_pending = db.query(InsuranceClaim).filter(
        InsuranceClaim.status == ClaimStatus.PREAUTH_REQUESTED).count()
    submitted = db.query(InsuranceClaim).filter(
        InsuranceClaim.status == ClaimStatus.SUBMITTED).count()
    under_review = db.query(InsuranceClaim).filter(
        InsuranceClaim.status == ClaimStatus.UNDER_REVIEW).count()
    settled = db.query(InsuranceClaim).filter(
        InsuranceClaim.status == ClaimStatus.SETTLED).count()
    from sqlalchemy import func
    settled_amount = db.query(func.sum(InsuranceClaim.approved_amount)).filter(
        InsuranceClaim.status == ClaimStatus.SETTLED).scalar() or 0
    pending_amount = db.query(func.sum(InsuranceClaim.claimed_amount)).filter(
        InsuranceClaim.status.in_([ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW])).scalar() or 0
    return {"total_claims": total, "preauth_pending": preauth_pending,
            "submitted": submitted, "under_review": under_review,
            "settled": settled, "settled_amount": round(settled_amount, 2),
            "pending_amount": round(pending_amount, 2)}


