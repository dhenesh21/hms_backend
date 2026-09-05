from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date, Time)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class WorklistStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class DICOMStudy(Base):
    """
    Items 247/248 (DICOM/PACS) as an international standard (NEMA/ACR — not
    a vendor product) rather than a specific PACS connection. This tracks
    DICOM-standard identifiers (Study/Series/SOP Instance UIDs) so images
    already recorded in `RadiologyImage` (Group 1/4) can be correctly
    referenced in a real DICOM network exchange later. What's genuinely
    NOT built: the DICOM network protocol itself (C-STORE/C-FIND/C-MOVE)
    and Modality Worklist's SCP service — those need `pydicom`/`pynetdicom`
    (not installable in this environment, no network) and a real PACS or
    imaging modality on the other end to test against. This is the metadata
    layer those would read from and write to, not a substitute for them.

    UID note: DICOM UIDs need an organization-specific root OID (registered
    with an authority like the DICOM UID registry) to be globally unique in
    a real multi-institution exchange. `services/dicom_uid.py` generates
    syntactically valid UIDs under a PLACEHOLDER root
    (`2.25.<random>`, the "UUID-derived OID" scheme DICOM itself defines for
    exactly this situation) — swap in your organization's registered root
    before any real external DICOM exchange; the placeholder is fine for
    internal use but not for claiming global uniqueness against outside
    systems.
    """
    __tablename__ = "dicom_studies"

    id = Column(Integer, primary_key=True, index=True)
    study_instance_uid = Column(String(100), unique=True, nullable=False)
    radiology_order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    accession_number = Column(String(50), nullable=True)
    study_date = Column(Date, nullable=True)
    study_time = Column(Time, nullable=True)
    study_description = Column(String(300), nullable=True)
    referring_physician = Column(String(200), nullable=True)
    modality = Column(String(20), nullable=True)     # CT, MR, CR, US, etc — DICOM modality codes

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DICOMSeries(Base):
    __tablename__ = "dicom_series"

    id = Column(Integer, primary_key=True, index=True)
    series_instance_uid = Column(String(100), unique=True, nullable=False)
    study_id = Column(Integer, ForeignKey("dicom_studies.id"), nullable=False)
    series_number = Column(Integer, nullable=True)
    modality = Column(String(20), nullable=True)
    body_part_examined = Column(String(100), nullable=True)
    series_description = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DICOMInstance(Base):
    """One DICOM image/frame within a series — links to the actual stored
    file via the existing RadiologyImage record (Group 1/4), this table
    just adds the DICOM-standard identifier for that file."""
    __tablename__ = "dicom_instances"

    id = Column(Integer, primary_key=True, index=True)
    sop_instance_uid = Column(String(100), unique=True, nullable=False)
    series_id = Column(Integer, ForeignKey("dicom_series.id"), nullable=False)
    radiology_image_id = Column(Integer, ForeignKey("radiology_images.id"), nullable=True)
    instance_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ModalityWorklistItem(Base):
    """
    DICOM Modality Worklist (MWL) entry — the standard mechanism by which an
    imaging device (CT/MR/X-ray scanner) queries for its scheduled patients
    instead of a technologist re-typing demographics at the console. This
    table is what a real MWL SCP service would serve; the SCP network
    service itself isn't implemented here (see class docstring above).
    """
    __tablename__ = "modality_worklist_items"

    id = Column(Integer, primary_key=True, index=True)
    radiology_order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=False)
    accession_number = Column(String(50), nullable=False, unique=True)
    scheduled_station_ae_title = Column(String(50), nullable=True)   # target modality's DICOM AE title
    scheduled_procedure_step_start_date = Column(Date, nullable=True)
    scheduled_procedure_step_start_time = Column(Time, nullable=True)
    modality = Column(String(20), nullable=True)
    requested_procedure_description = Column(String(300), nullable=True)
    status = Column(Enum(WorklistStatus), default=WorklistStatus.SCHEDULED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
