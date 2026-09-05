from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.medical_coding import MedicalCode, PatientCoding, CodeType
from app.models.billing import Bill
from app.models.user import User
from app.schemas.medical_coding import (
    MedicalCodeCreate,
    MedicalCodeResponse,
    PatientCodingCreate,
    PatientCodingResponse,
    RCMWorklistItem,
)

router = APIRouter(prefix="/medical-coding", tags=["Medical Coding & RCM"])


# ── CODE MASTER ─────────────────────────────────────────────

@router.post("/codes", response_model=MedicalCodeResponse, status_code=201)
async def create_code(
    data: MedicalCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(MedicalCode).filter(MedicalCode.code_system == data.code_system, MedicalCode.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="This code already exists in the master")
    code = MedicalCode(**data.model_dump())
    db.add(code)
    db.commit()
    db.refresh(code)
    return code


@router.get("/codes", response_model=list[MedicalCodeResponse])
async def list_codes(
    code_system: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(MedicalCode).filter(MedicalCode.is_active == 1)
    if code_system:
        q = q.filter(MedicalCode.code_system == code_system)
    if search:
        like = f"%{search}%"
        q = q.filter((MedicalCode.code.ilike(like)) | (MedicalCode.description.ilike(like)))
    return q.order_by(MedicalCode.code).limit(100).all()


# ── PATIENT CODING ─────────────────────────────────────────────

@router.post("/patient-coding", response_model=PatientCodingResponse, status_code=201)
async def code_bill(
    data: PatientCodingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = db.query(Bill).filter(Bill.id == data.bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    code = db.query(MedicalCode).filter(MedicalCode.id == data.code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Medical code not found")

    entry = PatientCoding(**data.model_dump(), coded_by=current_user.id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/patient-coding", response_model=list[PatientCodingResponse])
async def list_patient_coding(
    bill_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PatientCoding)
    if bill_id:
        q = q.filter(PatientCoding.bill_id == bill_id)
    return q.order_by(PatientCoding.coded_at.desc()).limit(200).all()


# ── RCM WORKLIST ─────────────────────────────────────────────

@router.get("/rcm/worklist", response_model=list[RCMWorklistItem])
async def rcm_worklist(
    ready_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bills = db.query(Bill).filter(Bill.insurance_claim_id.isnot(None)).order_by(Bill.bill_date.desc()).limit(200).all()
    results = []
    for bill in bills:
        codings = db.query(PatientCoding).filter(PatientCoding.bill_id == bill.id).all()
        has_diagnosis = any(c.code_type == CodeType.DIAGNOSIS for c in codings)
        has_procedure = any(c.code_type == CodeType.PROCEDURE for c in codings)
        coding_complete = has_diagnosis and has_procedure
        results.append(RCMWorklistItem(
            bill_id=bill.id,
            bill_number=bill.bill_number,
            patient_id=bill.patient_id,
            gross_total=bill.gross_total,
            has_diagnosis_code=has_diagnosis,
            has_procedure_code=has_procedure,
            is_coding_complete=coding_complete,
            insurance_claim_id=bill.insurance_claim_id,
            ready_for_claim_submission=coding_complete,
        ))
    if ready_only:
        results = [r for r in results if r.ready_for_claim_submission]
    return results


@router.get("/dashboard/stats")
async def coding_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_codes = db.query(MedicalCode).filter(MedicalCode.is_active == 1).count()
    total_coded_bills = db.query(PatientCoding.bill_id).distinct().count()

    bills = db.query(Bill).filter(Bill.insurance_claim_id.isnot(None)).all()
    pending_claims = 0
    for bill in bills:
        codings = db.query(PatientCoding).filter(PatientCoding.bill_id == bill.id).all()
        has_diagnosis = any(c.code_type == CodeType.DIAGNOSIS for c in codings)
        has_procedure = any(c.code_type == CodeType.PROCEDURE for c in codings)
        if not (has_diagnosis and has_procedure):
            pending_claims += 1

    return {
        "total_codes": total_codes,
        "total_coded_bills": total_coded_bills,
        "insurance_bills_pending_coding": pending_claims,
    }
