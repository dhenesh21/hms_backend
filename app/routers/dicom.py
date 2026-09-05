from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dicom import DICOMStudy, DICOMSeries, DICOMInstance, ModalityWorklistItem, WorklistStatus
from app.models.user import User
from app.services.dicom_uid import generate_dicom_uid, generate_accession_number
from app.schemas.dicom import (
    DICOMStudyCreate, DICOMStudyResponse,
    DICOMSeriesCreate, DICOMSeriesResponse,
    DICOMInstanceCreate, DICOMInstanceResponse,
    WorklistItemCreate, WorklistItemUpdate, WorklistItemResponse,
)

router = APIRouter(prefix="/dicom", tags=["DICOM / PACS (Interoperability)"])


@router.post("/studies", response_model=DICOMStudyResponse, status_code=201)
async def create_study(data: DICOMStudyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    study = DICOMStudy(**data.model_dump(), study_instance_uid=generate_dicom_uid(),
                        accession_number=generate_accession_number())
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


@router.get("/studies/order/{order_id}", response_model=List[DICOMStudyResponse])
async def list_studies_for_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DICOMStudy).filter(DICOMStudy.radiology_order_id == order_id).all()


@router.post("/series", response_model=DICOMSeriesResponse, status_code=201)
async def create_series(data: DICOMSeriesCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    series = DICOMSeries(**data.model_dump(), series_instance_uid=generate_dicom_uid())
    db.add(series)
    db.commit()
    db.refresh(series)
    return series


@router.get("/series/study/{study_id}", response_model=List[DICOMSeriesResponse])
async def list_series_for_study(study_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DICOMSeries).filter(DICOMSeries.study_id == study_id).all()


@router.post("/instances", response_model=DICOMInstanceResponse, status_code=201)
async def create_instance(data: DICOMInstanceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    instance = DICOMInstance(**data.model_dump(), sop_instance_uid=generate_dicom_uid())
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.get("/instances/series/{series_id}", response_model=List[DICOMInstanceResponse])
async def list_instances_for_series(series_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DICOMInstance).filter(DICOMInstance.series_id == series_id).all()


# ── MODALITY WORKLIST (MWL) ────────────────────────────
@router.post("/worklist", response_model=WorklistItemResponse, status_code=201)
async def create_worklist_item(data: WorklistItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = ModalityWorklistItem(**data.model_dump(), accession_number=generate_accession_number())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/worklist", response_model=List[WorklistItemResponse])
async def list_worklist(status: WorklistStatus = WorklistStatus.SCHEDULED, ae_title: Optional[str] = None,
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """What a real MWL SCP would serve to a scanner querying for its worklist —
    here exposed as a normal REST list for staff/testing use."""
    q = db.query(ModalityWorklistItem).filter(ModalityWorklistItem.status == status)
    if ae_title:
        q = q.filter(ModalityWorklistItem.scheduled_station_ae_title == ae_title)
    return q.all()


@router.patch("/worklist/{item_id}", response_model=WorklistItemResponse)
async def update_worklist_item(item_id: int, data: WorklistItemUpdate, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    item = db.query(ModalityWorklistItem).filter(ModalityWorklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Worklist item not found")
    item.status = data.status
    db.commit()
    db.refresh(item)
    return item
