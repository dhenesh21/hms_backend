from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.provider_registry import ProviderRegistryEntry
from app.models.user import User
from app.schemas.provider_registry import ProviderRegistryCreate, ProviderRegistryUpdate, ProviderRegistryResponse

router = APIRouter(prefix="/provider-registry", tags=["Provider Registry"])


@router.post("", response_model=ProviderRegistryResponse, status_code=201)
async def create_entry(data: ProviderRegistryCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    entry = ProviderRegistryEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=List[ProviderRegistryResponse])
async def list_entries(is_internal: Optional[bool] = None, search: Optional[str] = None,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(ProviderRegistryEntry)
    if is_internal is not None:
        q = q.filter(ProviderRegistryEntry.is_internal == is_internal)
    if search:
        q = q.filter(ProviderRegistryEntry.full_name.ilike(f"%{search}%"))
    return q.all()


@router.get("/{entry_id}", response_model=ProviderRegistryResponse)
async def get_entry(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(ProviderRegistryEntry).filter(ProviderRegistryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Provider registry entry not found")
    return entry


@router.patch("/{entry_id}", response_model=ProviderRegistryResponse)
async def update_entry(entry_id: int, data: ProviderRegistryUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    entry = db.query(ProviderRegistryEntry).filter(ProviderRegistryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Provider registry entry not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry
