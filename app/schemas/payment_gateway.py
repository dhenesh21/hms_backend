from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.models.payment_gateway import GatewayTxnStatus


class PaymentSessionCreate(BaseModel):
    bill_id: int
    patient_id: int
    amount: float
    currency: str = "INR"
    gateway_name: str = "manual"


class PaymentTransactionResponse(BaseModel):
    id: int
    bill_id: int
    patient_id: int
    gateway_name: str
    gateway_session_id: Optional[str]
    gateway_transaction_id: Optional[str]
    amount: float
    currency: str
    status: GatewayTxnStatus
    initiated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    gateway_transaction_id: str
    status: str
    raw: Optional[dict] = None
