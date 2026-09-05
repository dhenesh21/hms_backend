from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.facility_registry import FacilityRegistryEntry
from app.models.user import User
from app.schemas.facility_registry import FacilityRegistryCreate, FacilityRegistryUpdate, FacilityRegistryResponse

router = APIRouter(prefix="/facility-registry", tags=["Facility Registry"])


@router.post("", response_model=FacilityRegistryResponse, status_code=201)
async def create_entry(data: FacilityRegistryCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    entry = FacilityRegistryEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=List[FacilityRegistryResponse])
async def list_entries(facility_type: Optional[str] = None, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    q = db.query(FacilityRegistryEntry)
    if facility_type:
        q = q.filter(FacilityRegistryEntry.facility_type == facility_type)
    return q.all()


@router.get("/self", response_model=FacilityRegistryResponse)
async def get_self_entry(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(FacilityRegistryEntry).filter(FacilityRegistryEntry.is_self == True).first()
    if not entry:
        raise HTTPException(status_code=404, detail="This hospital's own facility registry entry hasn't been set up yet")
    return entry


@router.patch("/{entry_id}", response_model=FacilityRegistryResponse)
async def update_entry(entry_id: int, data: FacilityRegistryUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    entry = db.query(FacilityRegistryEntry).filter(FacilityRegistryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Facility registry entry not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry
