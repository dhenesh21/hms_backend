from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.patient_category import PatientCategoryProfile, PatientCategory
from app.models.user import User
from app.schemas.patient_category import PatientCategoryProfileUpsert, PatientCategoryProfileResponse

router = APIRouter(prefix="/patient-category", tags=["International / Corporate / Medical Tourism"])


@router.put("/profile", response_model=PatientCategoryProfileResponse)
async def upsert_profile(data: PatientCategoryProfileUpsert, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    profile = db.query(PatientCategoryProfile).filter(
        PatientCategoryProfile.patient_id == data.patient_id).first()
    if profile:
        for k, v in data.model_dump(exclude={"patient_id"}).items():
            setattr(profile, k, v)
    else:
        profile = PatientCategoryProfile(**data.model_dump())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/patient/{patient_id}", response_model=PatientCategoryProfileResponse)
async def get_profile(patient_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    profile = db.query(PatientCategoryProfile).filter(
        PatientCategoryProfile.patient_id == patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No category profile set for this patient (defaults to domestic)")
    return profile


@router.get("/by-category/{category}", response_model=List[PatientCategoryProfileResponse])
async def list_by_category(category: PatientCategory, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(PatientCategoryProfile).filter(PatientCategoryProfile.category == category).all()
