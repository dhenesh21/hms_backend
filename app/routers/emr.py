from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.emr import (PatientAllergy, ChronicCondition, MedicationHistory,
                              FamilyHistory, SurgicalHistory, ImmunizationRecord,
                              ClinicalDocument, DiagnosisRecord)
from app.models.user import User
from app.schemas.emr import (
    AllergyCreate, AllergyResponse,
    ChronicConditionCreate, ChronicConditionResponse,
    MedicationHistoryCreate, MedicationHistoryResponse,
    FamilyHistoryCreate, FamilyHistoryResponse,
    SurgicalHistoryCreate, SurgicalHistoryResponse,
    ImmunizationCreate, ImmunizationResponse,
    ClinicalDocumentCreate, ClinicalDocumentResponse,
    DiagnosisRecordCreate, DiagnosisRecordResponse,
    PatientEMRResponse
)

router = APIRouter(prefix="/emr", tags=["EMR / EHR"])


# ── FULL EMR SUMMARY ──────────────────────────────────
@router.get("/patient/{patient_id}", response_model=PatientEMRResponse)
async def get_patient_emr(patient_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return PatientEMRResponse(
        patient_id=patient_id,
        allergies=db.query(PatientAllergy).filter(PatientAllergy.patient_id == patient_id, PatientAllergy.is_active == True).all(),
        chronic_conditions=db.query(ChronicCondition).filter(ChronicCondition.patient_id == patient_id, ChronicCondition.is_active == True).all(),
        medication_history=db.query(MedicationHistory).filter(MedicationHistory.patient_id == patient_id).all(),
        family_history=db.query(FamilyHistory).filter(FamilyHistory.patient_id == patient_id).all(),
        surgical_history=db.query(SurgicalHistory).filter(SurgicalHistory.patient_id == patient_id).all(),
        immunizations=db.query(ImmunizationRecord).filter(ImmunizationRecord.patient_id == patient_id).all(),
        documents=db.query(ClinicalDocument).filter(ClinicalDocument.patient_id == patient_id, ClinicalDocument.is_active == True).all(),
        diagnosis_records=db.query(DiagnosisRecord).filter(DiagnosisRecord.patient_id == patient_id).order_by(DiagnosisRecord.diagnosis_date.desc()).all()
    )


# ── ALLERGIES ─────────────────────────────────────────
@router.post("/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(data: AllergyCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    allergy = PatientAllergy(**data.model_dump(), reported_by=current_user.id)
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.get("/allergies/{patient_id}", response_model=list[AllergyResponse])
async def get_allergies(patient_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    return db.query(PatientAllergy).filter(
        PatientAllergy.patient_id == patient_id,
        PatientAllergy.is_active == True
    ).all()


@router.delete("/allergies/{allergy_id}")
async def delete_allergy(allergy_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    allergy = db.query(PatientAllergy).filter(PatientAllergy.id == allergy_id).first()
    if not allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")
    allergy.is_active = False
    db.commit()
    return {"message": "Allergy removed"}


# ── CHRONIC CONDITIONS ────────────────────────────────
@router.post("/conditions", response_model=ChronicConditionResponse, status_code=201)
async def add_condition(data: ChronicConditionCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    cond = ChronicCondition(**data.model_dump())
    db.add(cond)
    db.commit()
    db.refresh(cond)
    return cond


@router.get("/conditions/{patient_id}", response_model=list[ChronicConditionResponse])
async def get_conditions(patient_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(ChronicCondition).filter(
        ChronicCondition.patient_id == patient_id,
        ChronicCondition.is_active == True
    ).all()


# ── MEDICATION HISTORY ────────────────────────────────
@router.post("/medications", response_model=MedicationHistoryResponse, status_code=201)
async def add_medication(data: MedicationHistoryCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    med = MedicationHistory(**data.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


@router.get("/medications/{patient_id}", response_model=list[MedicationHistoryResponse])
async def get_medications(patient_id: int, current_only: bool = Query(False),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    query = db.query(MedicationHistory).filter(MedicationHistory.patient_id == patient_id)
    if current_only:
        query = query.filter(MedicationHistory.is_current == True)
    return query.all()


# ── FAMILY HISTORY ────────────────────────────────────
@router.post("/family-history", response_model=FamilyHistoryResponse, status_code=201)
async def add_family_history(data: FamilyHistoryCreate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    fh = FamilyHistory(**data.model_dump())
    db.add(fh)
    db.commit()
    db.refresh(fh)
    return fh


@router.get("/family-history/{patient_id}", response_model=list[FamilyHistoryResponse])
async def get_family_history(patient_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return db.query(FamilyHistory).filter(FamilyHistory.patient_id == patient_id).all()


# ── SURGICAL HISTORY ──────────────────────────────────
@router.post("/surgical-history", response_model=SurgicalHistoryResponse, status_code=201)
async def add_surgical_history(data: SurgicalHistoryCreate, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    sh = SurgicalHistory(**data.model_dump())
    db.add(sh)
    db.commit()
    db.refresh(sh)
    return sh


@router.get("/surgical-history/{patient_id}", response_model=list[SurgicalHistoryResponse])
async def get_surgical_history(patient_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    return db.query(SurgicalHistory).filter(SurgicalHistory.patient_id == patient_id).all()


# ── IMMUNIZATIONS ─────────────────────────────────────
@router.post("/immunizations", response_model=ImmunizationResponse, status_code=201)
async def add_immunization(data: ImmunizationCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    imm = ImmunizationRecord(**data.model_dump())
    db.add(imm)
    db.commit()
    db.refresh(imm)
    return imm


@router.get("/immunizations/{patient_id}", response_model=list[ImmunizationResponse])
async def get_immunizations(patient_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(ImmunizationRecord).filter(
        ImmunizationRecord.patient_id == patient_id
    ).order_by(ImmunizationRecord.administered_date.desc()).all()


# ── CLINICAL DOCUMENTS ────────────────────────────────
@router.post("/documents", response_model=ClinicalDocumentResponse, status_code=201)
async def add_document(data: ClinicalDocumentCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    doc = ClinicalDocument(**data.model_dump(), uploaded_by=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/documents/{patient_id}", response_model=list[ClinicalDocumentResponse])
async def get_documents(patient_id: int,
                        doc_type: Optional[str] = Query(None),
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    query = db.query(ClinicalDocument).filter(
        ClinicalDocument.patient_id == patient_id,
        ClinicalDocument.is_active == True
    )
    if doc_type:
        query = query.filter(ClinicalDocument.document_type == doc_type)
    return query.order_by(ClinicalDocument.created_at.desc()).all()


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    doc = db.query(ClinicalDocument).filter(ClinicalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_active = False
    db.commit()
    return {"message": "Document removed"}


# ── DIAGNOSIS RECORDS ─────────────────────────────────
@router.post("/diagnosis", response_model=DiagnosisRecordResponse, status_code=201)
async def add_diagnosis(data: DiagnosisRecordCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    diag = DiagnosisRecord(**data.model_dump())
    db.add(diag)
    db.commit()
    db.refresh(diag)
    return diag


@router.get("/diagnosis/{patient_id}", response_model=list[DiagnosisRecordResponse])
async def get_diagnoses(patient_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    return db.query(DiagnosisRecord).filter(
        DiagnosisRecord.patient_id == patient_id
    ).order_by(DiagnosisRecord.diagnosis_date.desc()).all()


