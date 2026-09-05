from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.fertility import FertilityPatientProfile, FertilityCycle, FertilityMonitoringVisit
from app.models.user import User
from app.schemas.fertility import (
    FertilityProfileCreate, FertilityProfileResponse,
    FertilityCycleCreate, FertilityCycleUpdate, FertilityCycleResponse,
    MonitoringVisitCreate, MonitoringVisitResponse,
)

router = APIRouter(prefix="/fertility", tags=["Fertility / IVF"])


@router.post("/profiles", response_model=FertilityProfileResponse, status_code=201)
async def create_profile(data: FertilityProfileCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    existing = db.query(FertilityPatientProfile).filter(FertilityPatientProfile.patient_id == data.patient_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Fertility profile already exists for this patient")
    profile = FertilityPatientProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles/patient/{patient_id}", response_model=FertilityProfileResponse)
async def get_profile(patient_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    profile = db.query(FertilityPatientProfile).filter(FertilityPatientProfile.patient_id == patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No fertility profile for this patient")
    return profile


@router.post("/cycles", response_model=FertilityCycleResponse, status_code=201)
async def start_cycle(data: FertilityCycleCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    cycle = FertilityCycle(**data.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/cycles/profile/{profile_id}", response_model=List[FertilityCycleResponse])
async def list_cycles(profile_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return db.query(FertilityCycle).filter(
        FertilityCycle.profile_id == profile_id
    ).order_by(FertilityCycle.created_at.desc()).all()


@router.patch("/cycles/{cycle_id}", response_model=FertilityCycleResponse)
async def update_cycle(cycle_id: int, data: FertilityCycleUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    cycle = db.query(FertilityCycle).filter(FertilityCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cycle, k, v)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.post("/monitoring-visits", response_model=MonitoringVisitResponse, status_code=201)
async def add_monitoring_visit(data: MonitoringVisitCreate, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    visit = FertilityMonitoringVisit(**data.model_dump())
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/monitoring-visits/cycle/{cycle_id}", response_model=List[MonitoringVisitResponse])
async def list_monitoring_visits(cycle_id: int, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    return db.query(FertilityMonitoringVisit).filter(
        FertilityMonitoringVisit.cycle_id == cycle_id
    ).order_by(FertilityMonitoringVisit.visit_date).all()
