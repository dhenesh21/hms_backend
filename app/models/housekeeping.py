from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class CleaningTaskType(str, enum.Enum):
    ROUTINE = "routine"           # scheduled daily/shift cleaning
    DISCHARGE_CLEANING = "discharge_cleaning"  # after a patient is discharged
    DEEP_CLEANING = "deep_cleaning"
    SPILL_RESPONSE = "spill_response"


class CleaningTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"  # supervisor sign-off


class WasteType(str, enum.Enum):
    GENERAL = "general"
    BIOMEDICAL = "biomedical"
    SHARPS = "sharps"
    HAZARDOUS = "hazardous"


class CleaningTask(Base):
    """
    A single cleaning task - roadmap's "Cleaning Schedule", "Ward Cleaning",
    "Room Cleaning". Can target a ward, a specific bed, or a general area
    (area_name for non-bed locations like corridors, OT, reception).
    """
    __tablename__ = "housekeeping_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(Enum(CleaningTaskType), default=CleaningTaskType.ROUTINE)
    status = Column(Enum(CleaningTaskStatus), default=CleaningTaskStatus.PENDING)

    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=True)
    area_name = Column(String(200), nullable=True)  # for non-bed areas

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LinenLog(Base):
    """Linen/laundry tracking - roadmap's "Linen Tracking" / "Laundry"."""
    __tablename__ = "housekeeping_linen_logs"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    item_name = Column(String(100), nullable=False)  # e.g. "Bedsheet", "Pillow Cover"
    quantity_sent = Column(Integer, default=0)
    quantity_received = Column(Integer, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    received_at = Column(DateTime(timezone=True), nullable=True)
    is_soiled = Column(String(20), default="normal")  # normal / soiled / infected
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)


class WasteLog(Base):
    """Biomedical/general waste tracking - roadmap's "Waste Management" /
    "Biomedical Waste"."""
    __tablename__ = "housekeeping_waste_logs"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    waste_type = Column(Enum(WasteType), default=WasteType.GENERAL)
    weight_kg = Column(Float, nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    collected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    disposed_at = Column(DateTime(timezone=True), nullable=True)
    disposal_method = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
