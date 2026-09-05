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


class EquipmentStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    UNDER_MAINTENANCE = "under_maintenance"
    OUT_OF_SERVICE = "out_of_service"
    DECOMMISSIONED = "decommissioned"


class MaintenanceType(str, enum.Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    CALIBRATION = "calibration"


class ServiceRequestStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ServiceRequestPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(30), unique=True, index=True, nullable=False)

    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    model_number = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)

    department = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)

    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.OPERATIONAL)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    warranty_expiry = Column(DateTime(timezone=True), nullable=True)
    amc_expiry = Column(DateTime(timezone=True), nullable=True)
    next_calibration_due = Column(DateTime(timezone=True), nullable=True)

    purchase_cost = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    maintenance_logs = relationship("EquipmentMaintenanceLog", back_populates="equipment")


class EquipmentMaintenanceLog(Base):
    __tablename__ = "equipment_maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)

    maintenance_type = Column(Enum(MaintenanceType), default=MaintenanceType.PREVENTIVE)
    description = Column(Text, nullable=False)
    performed_by = Column(String(200), nullable=True)
    cost = Column(Float, nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    next_due_date = Column(DateTime(timezone=True), nullable=True)

    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    equipment = relationship("Equipment", back_populates="maintenance_logs")


class FacilityServiceRequest(Base):
    __tablename__ = "facility_service_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(20), unique=True, index=True, nullable=False)

    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)
    priority = Column(Enum(ServiceRequestPriority), default=ServiceRequestPriority.MEDIUM)
    status = Column(Enum(ServiceRequestStatus), default=ServiceRequestStatus.OPEN)

    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)

    raised_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    raised_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_to = Column(String(200), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
