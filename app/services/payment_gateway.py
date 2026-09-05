"""
Item 252 (Payment APIs) as protocol-level plumbing, not a specific gateway.
Unlike Telemedicine's video vendor (where Jitsi's public server is a
legitimate, genuinely free, zero-setup default), there is no equivalent
"free universal payment gateway" — moving real money always needs a real
merchant account and real credentials from a specific provider (Razorpay,
Stripe, PayU, etc). So instead of a working default, what's built here is
the interface every gateway adapter should implement, plus a NullGateway
that fails LOUDLY and clearly rather than silently pretending to work —
better than either (a) not building the plumbing at all, or (b) building a
fake gateway that looks functional in a demo and then breaks in production.

To activate a real gateway: implement this Protocol for your chosen
provider's SDK (most have a Python SDK you'd add to requirements.txt), then
register it in `GATEWAY_REGISTRY` below.
"""
from typing import Protocol, Optional
from dataclasses import dataclass


@dataclass
class PaymentSession:
    session_id: str
    checkout_url: Optional[str]     # where to redirect the patient, if the gateway is redirect-based


@dataclass
class PaymentVerification:
    status: str      # "success", "pending", "failed"
    gateway_transaction_id: Optional[str]
    raw: dict


class PaymentGatewayInterface(Protocol):
    async def create_session(self, amount: float, currency: str, bill_id: int, patient_id: int) -> PaymentSession: ...
    async def verify_payment(self, gateway_transaction_id: str) -> PaymentVerification: ...
    async def refund(self, gateway_transaction_id: str, amount: float) -> PaymentVerification: ...


class NullGateway:
    """The only gateway registered by default. Every method raises with a
    clear message rather than pretending to process a real payment — an API
    that silently "succeeds" without moving real money would be far worse
    than one that fails loudly and tells you exactly what to configure."""

    async def create_session(self, amount: float, currency: str, bill_id: int, patient_id: int) -> PaymentSession:
        raise NotImplementedError(
            "No payment gateway is configured. Implement PaymentGatewayInterface "
            "for your chosen provider (Razorpay/Stripe/PayU/etc) and register it "
            "in GATEWAY_REGISTRY in services/payment_gateway.py."
        )

    async def verify_payment(self, gateway_transaction_id: str) -> PaymentVerification:
        raise NotImplementedError("No payment gateway is configured.")

    async def refund(self, gateway_transaction_id: str, amount: float) -> PaymentVerification:
        raise NotImplementedError("No payment gateway is configured.")


GATEWAY_REGISTRY: dict[str, PaymentGatewayInterface] = {
    "manual": NullGateway(),   # placeholder name; swap in a real adapter, e.g. GATEWAY_REGISTRY["razorpay"] = RazorpayGateway(...)
}


def get_gateway(name: str) -> PaymentGatewayInterface:
    if name not in GATEWAY_REGISTRY:
        raise ValueError(f"Unknown payment gateway '{name}'. Registered: {list(GATEWAY_REGISTRY.keys())}")
    return GATEWAY_REGISTRY[name]
