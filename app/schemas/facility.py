from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.facility import EquipmentStatus, MaintenanceType, ServiceRequestStatus, ServiceRequestPriority


class EquipmentCreate(BaseModel):
    asset_code: str
    name: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    amc_expiry: Optional[datetime] = None
    next_calibration_due: Optional[datetime] = None
    purchase_cost: Optional[float] = None
    notes: Optional[str] = None


class EquipmentUpdate(BaseModel):
    status: Optional[EquipmentStatus] = None
    location: Optional[str] = None
    amc_expiry: Optional[datetime] = None
    next_calibration_due: Optional[datetime] = None
    notes: Optional[str] = None


class EquipmentResponse(BaseModel):
    id: int
    asset_code: str
    name: str
    category: Optional[str]
    manufacturer: Optional[str]
    model_number: Optional[str]
    serial_number: Optional[str]
    department: Optional[str]
    location: Optional[str]
    status: EquipmentStatus
    purchase_date: Optional[datetime]
    warranty_expiry: Optional[datetime]
    amc_expiry: Optional[datetime]
    next_calibration_due: Optional[datetime]
    purchase_cost: Optional[float]
    notes: Optional[str]

    class Config:
        from_attributes = True


class MaintenanceLogCreate(BaseModel):
    maintenance_type: MaintenanceType = MaintenanceType.PREVENTIVE
    description: str
    performed_by: Optional[str] = None
    cost: Optional[float] = None
    next_due_date: Optional[datetime] = None


class MaintenanceLogResponse(MaintenanceLogCreate):
    id: int
    equipment_id: int
    performed_at: datetime

    class Config:
        from_attributes = True


class ServiceRequestCreate(BaseModel):
    category: str
    description: str
    location: Optional[str] = None
    priority: ServiceRequestPriority = ServiceRequestPriority.MEDIUM
    equipment_id: Optional[int] = None


class ServiceRequestUpdate(BaseModel):
    status: Optional[ServiceRequestStatus] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class ServiceRequestResponse(BaseModel):
    id: int
    request_number: str
    category: str
    description: str
    location: Optional[str]
    priority: ServiceRequestPriority
    status: ServiceRequestStatus
    equipment_id: Optional[int]
    raised_at: datetime
    assigned_to: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]

    class Config:
        from_attributes = True
