from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Enum, JSON
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class GatewayTxnStatus(str, enum.Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentGatewayTransaction(Base):
    """
    Item 252 (Payment APIs) — tracks an online payment attempt through
    whichever gateway is actually configured (see
    services/payment_gateway.py for the pluggable interface). Deliberately
    stores only a gateway-returned reference/token, never a card number or
    other cardholder data — real card handling should happen entirely on
    the gateway's own hosted checkout page (Stripe Checkout, Razorpay's
    hosted page, etc), which is standard PCI-DSS scope reduction practice:
    this system never needs to be in PCI scope if it never touches card
    data directly.
    """
    __tablename__ = "payment_gateway_transactions"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    gateway_name = Column(String(50), nullable=False)     # "razorpay", "stripe", "manual", etc
    gateway_session_id = Column(String(300), nullable=True)
    gateway_transaction_id = Column(String(300), nullable=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(Enum(GatewayTxnStatus), default=GatewayTxnStatus.INITIATED)

    failure_reason = Column(Text, nullable=True)
    raw_webhook_payload = Column(JSON, nullable=True)   # last webhook received, for support/debugging

    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
