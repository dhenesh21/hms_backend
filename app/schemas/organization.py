from pydantic import BaseModel
from typing import Optional


class BranchCreate(BaseModel):
    branch_code: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_head_office: bool = False


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class BranchResponse(BaseModel):
    id: int
    branch_code: str
    name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_head_office: bool
    is_active: bool

    class Config:
        from_attributes = True


class TaxRateCreate(BaseModel):
    name: str
    percent: float
    is_default: bool = False


class TaxRateResponse(BaseModel):
    id: int
    name: str
    percent: float
    is_default: bool
    is_active: bool

    class Config:
        from_attributes = True


class PaymentModeMasterCreate(BaseModel):
    code: str
    display_name: str
    is_enabled: bool = True


class PaymentModeMasterResponse(BaseModel):
    id: int
    code: str
    display_name: str
    is_enabled: bool

    class Config:
        from_attributes = True
