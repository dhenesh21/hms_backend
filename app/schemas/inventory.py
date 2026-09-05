from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.inventory import ItemCategory, POStatus, MovementType


class ItemCreate(BaseModel):
    item_code: str
    name: str
    category: ItemCategory = ItemCategory.CONSUMABLE
    unit: str = "piece"
    reorder_level: int = 0


class ItemResponse(BaseModel):
    id: int
    item_code: str
    name: str
    category: ItemCategory
    unit: str
    reorder_level: int
    is_active: bool

    class Config:
        from_attributes = True


class VendorCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class VendorResponse(VendorCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class POItemInput(BaseModel):
    item_id: int
    quantity_ordered: int
    unit_price: float


class POCreate(BaseModel):
    vendor_id: int
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: list[POItemInput]


class POItemResponse(BaseModel):
    id: int
    item_id: int
    quantity_ordered: int
    quantity_received: int
    unit_price: float

    class Config:
        from_attributes = True


class POResponse(BaseModel):
    id: int
    po_number: str
    vendor_id: int
    status: POStatus
    order_date: datetime
    expected_delivery_date: Optional[datetime]
    notes: Optional[str]
    items: list[POItemResponse] = []

    class Config:
        from_attributes = True


class GRNItemInput(BaseModel):
    po_item_id: int
    item_id: int
    quantity_received: int


class GRNCreate(BaseModel):
    po_id: int
    notes: Optional[str] = None
    items: list[GRNItemInput]


class GRNResponse(BaseModel):
    id: int
    grn_number: str
    po_id: int
    received_date: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class StockResponse(BaseModel):
    id: int
    item_id: int
    location: str
    quantity_available: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class MovementCreate(BaseModel):
    item_id: int
    movement_type: MovementType
    quantity: int
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    department: Optional[str] = None
    reason: Optional[str] = None


class MovementResponse(MovementCreate):
    id: int
    moved_at: datetime

    class Config:
        from_attributes = True
