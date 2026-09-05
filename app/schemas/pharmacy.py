from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.pharmacy import DrugCategory, DrugFormulation, DispenseStatus


class DrugMasterCreate(BaseModel):
    drug_code: str
    brand_name: str
    generic_name: str
    category: DrugCategory
    formulation: DrugFormulation
    strength: Optional[str] = None
    unit: str = "tablet"
    manufacturer: Optional[str] = None
    schedule: Optional[str] = None
    is_narcotic: bool = False
    hsn_code: Optional[str] = None
    tax_percent: float = 12.0
    reorder_level: int = 10
    known_interactions: Optional[str] = None
    contraindications: Optional[str] = None
    pregnancy_category: Optional[str] = None


class DrugMasterResponse(BaseModel):
    id: int
    drug_code: str
    brand_name: str
    generic_name: str
    category: DrugCategory
    formulation: DrugFormulation
    strength: Optional[str]
    unit: str
    manufacturer: Optional[str]
    schedule: Optional[str]
    is_narcotic: bool
    tax_percent: float
    reorder_level: int
    known_interactions: Optional[str]
    contraindications: Optional[str]
    pregnancy_category: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class DrugStockCreate(BaseModel):
    drug_id: int
    batch_number: str
    expiry_date: date
    manufacture_date: Optional[date] = None
    quantity_received: int
    purchase_price: float
    sale_price: float
    mrp: Optional[float] = None
    supplier_id: Optional[int] = None
    location: Optional[str] = None


class DrugStockResponse(BaseModel):
    id: int
    drug_id: int
    batch_number: str
    expiry_date: date
    quantity_received: int
    quantity_available: int
    purchase_price: float
    sale_price: float
    mrp: Optional[float]
    location: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class DrugWithStockResponse(BaseModel):
    id: int
    drug_code: str
    brand_name: str
    generic_name: str
    category: DrugCategory
    formulation: DrugFormulation
    strength: Optional[str]
    unit: str
    total_stock: int
    reorder_level: int
    is_low_stock: bool
    nearest_expiry: Optional[date]
    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    supplier_code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    drug_license_number: Optional[str] = None
    payment_terms: Optional[str] = None


class SupplierResponse(BaseModel):
    id: int
    supplier_code: str
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    gst_number: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class POItemCreate(BaseModel):
    drug_id: int
    quantity_ordered: int
    unit_price: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    expected_delivery: Optional[date] = None
    notes: Optional[str] = None
    items: List[POItemCreate]


class POItemResponse(BaseModel):
    id: int
    drug_id: int
    quantity_ordered: int
    quantity_received: int
    unit_price: float
    total_price: float
    class Config:
        from_attributes = True


class PurchaseOrderResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    order_date: date
    expected_delivery: Optional[date]
    status: str
    total_amount: float
    items: List[POItemResponse] = []
    class Config:
        from_attributes = True


class DispenseItemCreate(BaseModel):
    drug_id: int
    drug_name: str
    quantity: int
    unit_price: float
    tax_percent: float = 0.0
    discount_percent: float = 0.0
    dosage_instructions: Optional[str] = None


class DispenseCreate(BaseModel):
    patient_id: int
    prescription_source: str = "opd"
    opd_visit_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    items: List[DispenseItemCreate]
    payment_mode: Optional[str] = None
    notes: Optional[str] = None


class DispenseItemResponse(BaseModel):
    id: int
    drug_id: int
    drug_name: str
    batch_number: Optional[str]
    expiry_date: Optional[date]
    quantity: int
    unit_price: float
    tax_amount: float
    discount_amount: float
    total_price: float
    dosage_instructions: Optional[str]
    class Config:
        from_attributes = True


class DispenseResponse(BaseModel):
    id: int
    dispense_number: str
    patient_id: int
    prescription_source: str
    status: DispenseStatus
    total_amount: float
    discount_amount: float
    tax_amount: float
    net_amount: float
    is_paid: bool
    items: List[DispenseItemResponse] = []
    created_at: datetime
    class Config:
        from_attributes = True


class StockAlertResponse(BaseModel):
    drug_id: int
    drug_code: str
    brand_name: str
    generic_name: str
    alert_type: str   # low_stock, expiring_soon, expired
    current_stock: int
    reorder_level: int
    nearest_expiry: Optional[date]
    days_to_expiry: Optional[int]


# ── DRUG RETURN (item 101) ─────────────────────────────
class DrugReturnCreate(BaseModel):
    direction: str    # "to_supplier" or "from_patient"
    drug_id: int
    stock_id: Optional[int] = None
    dispense_item_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: int
    reason: str


class DrugReturnDecision(BaseModel):
    notes: Optional[str] = None


class DrugReturnResponse(BaseModel):
    id: int
    return_number: str
    direction: str
    status: str
    drug_id: int
    quantity: int
    reason: str
    created_at: datetime
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True


# ── DRUG TRANSFER (item 102) ───────────────────────────
class DrugTransferCreate(BaseModel):
    stock_id: int
    to_location: str
    from_branch_id: Optional[int] = None
    to_branch_id: Optional[int] = None
    quantity: int
    reason: Optional[str] = None


class DrugTransferResponse(BaseModel):
    id: int
    transfer_number: str
    stock_id: int
    from_location: Optional[str]
    to_location: str
    quantity: int
    created_at: datetime
    class Config:
        from_attributes = True


# ── STOCK ADJUSTMENT (item 103) ────────────────────────
class StockAdjustmentCreate(BaseModel):
    stock_id: int
    reason: str    # damage, wastage, theft_loss, expiry_write_off, stock_count_correction
    new_quantity: int
    notes: Optional[str] = None


class StockAdjustmentResponse(BaseModel):
    id: int
    stock_id: int
    reason: str
    quantity_before: int
    quantity_after: int
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ── PURCHASE ORDER RECEIPT (item 107 - real GRN) ───────
class POReceiveItem(BaseModel):
    po_item_id: int
    quantity_received: int
    batch_number: str
    expiry_date: date
    manufacture_date: Optional[date] = None
    sale_price: float
    mrp: Optional[float] = None
    location: Optional[str] = None


class POReceiveRequest(BaseModel):
    items: List[POReceiveItem]
