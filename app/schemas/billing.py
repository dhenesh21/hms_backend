from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.billing import BillType, BillStatus, PaymentMode, ServiceCategory


class ServiceMasterCreate(BaseModel):
    service_code: str
    service_name: str
    category: ServiceCategory
    unit_price: float
    tax_percent: float = 0.0
    description: Optional[str] = None


class ServiceMasterResponse(BaseModel):
    id: int
    service_code: str
    service_name: str
    category: ServiceCategory
    unit_price: float
    tax_percent: float
    is_active: bool
    class Config:
        from_attributes = True


class PackageCreate(BaseModel):
    package_code: str
    package_name: str
    description: Optional[str] = None
    total_price: float
    validity_days: int = 30
    inclusions: List[str] = []


class PackageResponse(BaseModel):
    id: int
    package_code: str
    package_name: str
    description: Optional[str]
    total_price: float
    validity_days: int
    inclusions: List[str]
    is_active: bool
    class Config:
        from_attributes = True


# ── PACKAGE LINE ITEMS (items 142-143) ──────────────────
class PackageLineItemCreate(BaseModel):
    package_id: int
    service_id: int
    quantity: int = 1
    package_price: float
    is_optional: bool = False


class PackageLineItemResponse(BaseModel):
    id: int
    package_id: int
    service_id: int
    quantity: int
    package_price: float
    standalone_price: Optional[float]
    is_optional: bool
    class Config:
        from_attributes = True


class BillItemCreate(BaseModel):
    service_id: Optional[int] = None
    item_name: str
    category: ServiceCategory
    quantity: float = 1.0
    unit_price: float
    tax_percent: float = 0.0
    discount_percent: float = 0.0
    service_date: Optional[date] = None
    notes: Optional[str] = None


class BillItemResponse(BaseModel):
    id: int
    service_id: Optional[int]
    item_name: str
    category: ServiceCategory
    quantity: float
    unit_price: float
    tax_percent: float
    tax_amount: float
    discount_percent: float
    discount_amount: float
    total_price: float
    service_date: Optional[date]
    class Config:
        from_attributes = True


class BillCreate(BaseModel):
    patient_id: int
    bill_type: BillType
    opd_visit_id: Optional[int] = None
    ipd_admission_id: Optional[int] = None
    package_id: Optional[int] = None
    due_date: Optional[date] = None
    items: List[BillItemCreate] = []
    notes: Optional[str] = None


class BillUpdate(BaseModel):
    status: Optional[BillStatus] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_reason: Optional[str] = None
    notes: Optional[str] = None


class BillResponse(BaseModel):
    id: int
    bill_number: str
    patient_id: int
    bill_type: BillType
    status: BillStatus
    opd_visit_id: Optional[int]
    ipd_admission_id: Optional[int]
    bill_date: datetime
    due_date: Optional[date]
    subtotal: float
    tax_amount: float
    discount_amount: float
    discount_percent: float
    package_amount: float
    gross_total: float
    insurance_amount: float
    patient_liability: float
    paid_amount: float
    balance_amount: float
    items: List[BillItemResponse] = []
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


class BillSummaryResponse(BaseModel):
    id: int
    bill_number: str
    patient_id: int
    bill_type: BillType
    status: BillStatus
    gross_total: float
    paid_amount: float
    balance_amount: float
    bill_date: datetime
    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    bill_id: int
    patient_id: int
    amount: float
    payment_mode: PaymentMode
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_date: Optional[date] = None
    tpa_name: Optional[str] = None
    insurance_approval_code: Optional[str] = None
    notes: Optional[str] = None
    is_advance: bool = False


class PaymentResponse(BaseModel):
    id: int
    payment_number: str
    bill_id: int
    patient_id: int
    amount: float
    payment_mode: PaymentMode
    payment_date: datetime
    transaction_reference: Optional[str]
    is_advance: bool
    is_refund: bool
    class Config:
        from_attributes = True


class AdvancePaymentCreate(BaseModel):
    patient_id: int
    ipd_admission_id: Optional[int] = None
    amount: float
    payment_mode: PaymentMode
    transaction_reference: Optional[str] = None


class DiscountApproval(BaseModel):
    bill_id: int
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_reason: str


# ── REFUND WORKFLOW (items 146-149) ─────────────────────
class RefundRequestCreate(BaseModel):
    original_payment_id: int
    amount: float
    reason: str


class RefundApproval(BaseModel):
    notes: Optional[str] = None


class RefundReversal(BaseModel):
    reversal_reason: str


class RefundRequestResponse(BaseModel):
    id: int
    refund_number: str
    original_payment_id: int
    bill_id: int
    amount: float
    reason: str
    status: str
    refund_payment_id: Optional[int]
    created_at: datetime
    approved_at: Optional[datetime]
    reversed_at: Optional[datetime]
    class Config:
        from_attributes = True
