from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
import csv
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.terminology import TerminologyCode, TerminologyMapping, CodeSystem
from app.models.user import User
from app.schemas.terminology import (
    TerminologyCodeCreate, TerminologyCodeResponse,
    TerminologyMappingCreate, TerminologyMappingResponse, BulkImportResult,
)

router = APIRouter(prefix="/terminology", tags=["Terminology Repository"])


@router.post("/codes", response_model=TerminologyCodeResponse, status_code=201)
async def create_code(data: TerminologyCodeCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    code = TerminologyCode(**data.model_dump())
    db.add(code)
    db.commit()
    db.refresh(code)
    return code


@router.get("/codes/search", response_model=List[TerminologyCodeResponse])
async def search_codes(code_system: Optional[CodeSystem] = None, q: Optional[str] = None, limit: int = 50,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(TerminologyCode).filter(TerminologyCode.is_active == True)
    if code_system:
        query = query.filter(TerminologyCode.code_system == code_system)
    if q:
        query = query.filter(
            (TerminologyCode.display_name.ilike(f"%{q}%")) | (TerminologyCode.code.ilike(f"%{q}%"))
        )
    return query.limit(limit).all()


@router.get("/codes/{code_system}/{code}", response_model=TerminologyCodeResponse)
async def get_code(code_system: CodeSystem, code: str, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    entry = db.query(TerminologyCode).filter(
        TerminologyCode.code_system == code_system, TerminologyCode.code == code
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Code {code} not found in {code_system.value}")
    return entry


@router.post("/codes/bulk-import", response_model=BulkImportResult)
async def bulk_import_codes(code_system: CodeSystem, csv_content: str, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """
    Load a licensed code set (ICD-10/LOINC/SNOMED-CT export) via CSV — columns:
    code,display_name,description,parent_code (description/parent_code optional).
    This does NOT fetch or embed any official code set itself — that data
    must come from a licensed source you already hold; this only ingests it
    once you have the file. Skips codes that already exist for that system.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    imported, skipped = 0, 0
    for row in reader:
        code_val = row.get("code", "").strip()
        if not code_val:
            continue
        existing = db.query(TerminologyCode).filter(
            TerminologyCode.code_system == code_system, TerminologyCode.code == code_val
        ).first()
        if existing:
            skipped += 1
            continue
        db.add(TerminologyCode(
            code_system=code_system, code=code_val,
            display_name=row.get("display_name", code_val),
            description=row.get("description") or None,
            parent_code=row.get("parent_code") or None,
        ))
        imported += 1
    db.commit()
    return BulkImportResult(imported=imported, skipped_duplicates=skipped)


@router.post("/mappings", response_model=TerminologyMappingResponse, status_code=201)
async def create_mapping(data: TerminologyMappingCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    mapping = TerminologyMapping(**data.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/mappings/{code_id}", response_model=List[TerminologyMappingResponse])
async def get_mappings_for_code(code_id: int, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    return db.query(TerminologyMapping).filter(TerminologyMapping.source_code_id == code_id).all()
