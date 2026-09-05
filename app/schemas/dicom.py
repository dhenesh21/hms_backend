from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time, datetime
from app.models.dicom import WorklistStatus


class DICOMStudyCreate(BaseModel):
    radiology_order_id: int
    patient_id: int
    study_description: Optional[str] = None
    referring_physician: Optional[str] = None
    modality: Optional[str] = None


class DICOMStudyResponse(BaseModel):
    id: int
    study_instance_uid: str
    radiology_order_id: int
    patient_id: int
    accession_number: Optional[str]
    modality: Optional[str]
    study_description: Optional[str]

    class Config:
        from_attributes = True


class DICOMSeriesCreate(BaseModel):
    study_id: int
    series_number: Optional[int] = None
    modality: Optional[str] = None
    body_part_examined: Optional[str] = None
    series_description: Optional[str] = None


class DICOMSeriesResponse(BaseModel):
    id: int
    series_instance_uid: str
    study_id: int
    series_number: Optional[int]
    modality: Optional[str]

    class Config:
        from_attributes = True


class DICOMInstanceCreate(BaseModel):
    series_id: int
    radiology_image_id: Optional[int] = None
    instance_number: Optional[int] = None


class DICOMInstanceResponse(BaseModel):
    id: int
    sop_instance_uid: str
    series_id: int
    radiology_image_id: Optional[int]
    instance_number: Optional[int]

    class Config:
        from_attributes = True


class WorklistItemCreate(BaseModel):
    radiology_order_id: int
    scheduled_station_ae_title: Optional[str] = None
    scheduled_procedure_step_start_date: Optional[date] = None
    scheduled_procedure_step_start_time: Optional[time] = None
    modality: Optional[str] = None
    requested_procedure_description: Optional[str] = None


class WorklistItemUpdate(BaseModel):
    status: WorklistStatus


class WorklistItemResponse(BaseModel):
    id: int
    radiology_order_id: int
    accession_number: str
    scheduled_station_ae_title: Optional[str]
    scheduled_procedure_step_start_date: Optional[date]
    modality: Optional[str]
    status: WorklistStatus

    class Config:
        from_attributes = True
