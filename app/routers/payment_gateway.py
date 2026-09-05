from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.payment_gateway import PaymentGatewayTransaction, GatewayTxnStatus
from app.models.user import User
from app.services.payment_gateway import get_gateway
from app.schemas.payment_gateway import PaymentSessionCreate, PaymentTransactionResponse, WebhookPayload

router = APIRouter(prefix="/payment-gateway", tags=["Payment Gateway (Interoperability)"])


@router.post("/initiate", response_model=PaymentTransactionResponse, status_code=201)
async def initiate_payment(data: PaymentSessionCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """
    Fails with a clear 501 if no real gateway is registered (the default
    "manual" entry is a NullGateway — see services/payment_gateway.py). This
    is intentional: an endpoint that looks like it processes payment but
    doesn't move real money would be far more dangerous than one that says
    plainly "not configured yet."
    """
    txn = PaymentGatewayTransaction(
        bill_id=data.bill_id, patient_id=data.patient_id, gateway_name=data.gateway_name,
        amount=data.amount, currency=data.currency,
    )
    try:
        gateway = get_gateway(data.gateway_name)
        session = await gateway.create_session(data.amount, data.currency, data.bill_id, data.patient_id)
        txn.gateway_session_id = session.session_id
        txn.status = GatewayTxnStatus.PENDING
    except NotImplementedError as e:
        db.add(txn)
        db.commit()
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/transactions/bill/{bill_id}", response_model=List[PaymentTransactionResponse])
async def list_transactions_for_bill(bill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(PaymentGatewayTransaction).filter(PaymentGatewayTransaction.bill_id == bill_id).all()


@router.post("/webhook/{gateway_name}")
async def receive_webhook(gateway_name: str, payload: WebhookPayload, db: Session = Depends(get_db)):
    """
    No staff auth here deliberately — a real gateway's webhook is called by
    the gateway's own servers, not a logged-in user. A production version of
    this endpoint MUST verify the gateway's webhook signature (every real
    gateway provides one) before trusting the payload — that verification
    is gateway-specific and isn't implemented here since no real gateway is
    wired yet; add it as part of implementing that gateway's adapter.
    """
    txn = db.query(PaymentGatewayTransaction).filter(
        PaymentGatewayTransaction.gateway_transaction_id == payload.gateway_transaction_id,
        PaymentGatewayTransaction.gateway_name == gateway_name,
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="No matching transaction for this webhook")

    txn.raw_webhook_payload = payload.raw
    if payload.status == "success":
        txn.status = GatewayTxnStatus.SUCCESS
        txn.completed_at = datetime.now(timezone.utc)
    elif payload.status == "failed":
        txn.status = GatewayTxnStatus.FAILED
    db.commit()
    return {"message": "Webhook processed"}
