from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class SterilizationMethod(str, enum.Enum):
    AUTOCLAVE = "autoclave"
    ETO = "eto"          # Ethylene Oxide
    PLASMA = "plasma"     # Hydrogen Peroxide Plasma
    DRY_HEAT = "dry_heat"
    CHEMICAL = "chemical"


class CycleStatus(str, enum.Enum):
    RECEIVED = "received"          # dirty instruments received from OT/ward
    WASHING = "washing"
    STERILIZING = "sterilizing"
    QUALITY_CHECK = "quality_check"
    READY = "ready"                 # sterile, ready for dispatch
    DISPATCHED = "dispatched"        # sent back to OT/ward
    FAILED = "failed"                # failed biological/chemical indicator


class SterilizationCycle(Base):
    """
    One sterilization batch/cycle - roadmap's "CSSD / Sterile Services".
    Tracks an instrument set from dirty receipt through to sterile
    dispatch back to OT or a ward.
    """
    __tablename__ = "cssd_cycles"

    id = Column(Integer, primary_key=True, index=True)
    cycle_number = Column(String(20), unique=True, index=True, nullable=False)

    item_set_name = Column(String(200), nullable=False)  # e.g. "General Surgery Set A"
    quantity = Column(Integer, default=1)
    source_department = Column(String(100), nullable=True)  # e.g. "OT-1", "Ward 3B"

    method = Column(Enum(SterilizationMethod), default=SterilizationMethod.AUTOCLAVE)
    status = Column(Enum(CycleStatus), default=CycleStatus.RECEIVED)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
    sterilization_start = Column(DateTime(timezone=True), nullable=True)
    sterilization_end = Column(DateTime(timezone=True), nullable=True)
    quality_check_passed = Column(String(10), nullable=True)  # "pass" / "fail", nullable until checked
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_to = Column(String(100), nullable=True)

    batch_indicator_number = Column(String(50), nullable=True)  # biological indicator batch ref
    received_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
