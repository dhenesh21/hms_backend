from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.billing import (Bill, BillItem, Payment, AdvancePayment,
                                  ServiceMaster, BillingPackage, PackageLineItem,
                                  RefundRequest, RefundStatus,
                                  BillStatus, ServiceCategory, PaymentMode)
from app.models.user import User
from app.schemas.billing import (
    ServiceMasterCreate, ServiceMasterResponse,
    PackageCreate, PackageResponse,
    PackageLineItemCreate, PackageLineItemResponse,
    BillCreate, BillUpdate, BillResponse, BillSummaryResponse,
    PaymentCreate, PaymentResponse,
    AdvancePaymentCreate, DiscountApproval,
    RefundRequestCreate, RefundApproval, RefundReversal, RefundRequestResponse,
)

router = APIRouter(prefix="/billing", tags=["Billing & Accounts"])


# ── SERVICE MASTER ─────────────────────────────────────
@router.post("/services", response_model=ServiceMasterResponse, status_code=201)
async def create_service(data: ServiceMasterCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    svc = ServiceMaster(**data.model_dump())
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


@router.get("/services", response_model=list[ServiceMasterResponse])
async def list_services(category: Optional[ServiceCategory] = None,
                         search: Optional[str] = None,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(ServiceMaster).filter(ServiceMaster.is_active == True)
    if category:
        q = q.filter(ServiceMaster.category == category)
    if search:
        q = q.filter(ServiceMaster.service_name.ilike(f"%{search}%"))
    return q.order_by(ServiceMaster.service_name).all()


# ── PACKAGES ──────────────────────────────────────────
@router.post("/packages", response_model=PackageResponse, status_code=201)
async def create_package(data: PackageCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    pkg = BillingPackage(**data.model_dump())
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


@router.get("/packages", response_model=list[PackageResponse])
async def list_packages(db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return db.query(BillingPackage).filter(BillingPackage.is_active == True).all()


# ── PACKAGE LINE ITEMS (items 142-143) ──────────────────
@router.post("/packages/line-items", response_model=PackageLineItemResponse, status_code=201)
async def add_package_line_item(data: PackageLineItemCreate, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    package = db.query(BillingPackage).filter(BillingPackage.id == data.package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    service = db.query(ServiceMaster).filter(ServiceMaster.id == data.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    line = PackageLineItem(**data.model_dump(), standalone_price=service.unit_price)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.get("/packages/{package_id}/line-items", response_model=list[PackageLineItemResponse])
async def list_package_line_items(package_id: int, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    return db.query(PackageLineItem).filter(PackageLineItem.package_id == package_id).all()


@router.delete("/packages/line-items/{line_item_id}", status_code=204)
async def remove_package_line_item(line_item_id: int, db: Session = Depends(get_db),
                                    current_user: User = Depends(get_current_user)):
    line = db.query(PackageLineItem).filter(PackageLineItem.id == line_item_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line item not found")
    db.delete(line)
    db.commit()


# ── BILLS ─────────────────────────────────────────────
def calculate_bill_totals(bill: Bill):
    subtotal = 0.0
    tax_total = 0.0
    discount_total = 0.0
    for item in bill.items:
        item_subtotal = item.quantity * item.unit_price
        item_discount = item_subtotal * (item.discount_percent / 100)
        item_tax = (item_subtotal - item_discount) * (item.tax_percent / 100)
        item.discount_amount = round(item_discount, 2)
        item.tax_amount = round(item_tax, 2)
        item.total_price = round(item_subtotal - item_discount + item_tax, 2)
        subtotal += item_subtotal
        tax_total += item_tax
        discount_total += item_discount

    bill.subtotal = round(subtotal, 2)
    bill.tax_amount = round(tax_total, 2)
    bill_discount = discount_total + (subtotal * (bill.discount_percent or 0) / 100)
    bill.discount_amount = round(bill_discount, 2)
    bill.gross_total = round(subtotal + tax_total - bill_discount, 2)
    bill.patient_liability = round(bill.gross_total - bill.insurance_amount, 2)
    bill.balance_amount = round(bill.patient_liability - bill.paid_amount, 2)


@router.post("/bills", response_model=BillResponse, status_code=201)
async def create_bill(data: BillCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    prefix = {"opd": "OPD", "ipd": "IPD", "emergency": "EMG", "day_care": "DC"}.get(data.bill_type, "BILL")
    items_data = data.items
    bill_data = data.model_dump(exclude={"items"})

    attempt_base = next_sequence_number(db, Bill)
    bill = None
    last_error = None
    for i in range(MAX_RETRIES):
        bill_number = f"{prefix}BILL{attempt_base + i:06d}"
        bill = Bill(**bill_data, bill_number=bill_number, created_by=current_user.id)
        db.add(bill)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            bill = None
    if last_error:
        raise last_error

    for item_data in items_data:
        item_dict = item_data.model_dump()
        item_subtotal = item_dict["quantity"] * item_dict["unit_price"]
        item_discount = item_subtotal * (item_dict.get("discount_percent", 0) / 100)
        item_tax = (item_subtotal - item_discount) * (item_dict.get("tax_percent", 0) / 100)
        item = BillItem(
            **item_dict,
            bill_id=bill.id,
            discount_amount=round(item_discount, 2),
            tax_amount=round(item_tax, 2),
            total_price=round(item_subtotal - item_discount + item_tax, 2),
        )
        db.add(item)

    db.flush()
    db.refresh(bill)
    calculate_bill_totals(bill)
    bill.status = BillStatus.PENDING
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/bills", response_model=list[BillSummaryResponse])
async def list_bills(patient_id: Optional[int] = Query(None),
                     status: Optional[BillStatus] = Query(None),
                     bill_type: Optional[str] = Query(None),
                     from_date: Optional[date] = Query(None),
                     to_date: Optional[date] = Query(None),
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    q = db.query(Bill)
    if patient_id:
        q = q.filter(Bill.patient_id == patient_id)
    if status:
        q = q.filter(Bill.status == status)
    if bill_type:
        q = q.filter(Bill.bill_type == bill_type)
    if from_date:
        q = q.filter(func.cast(Bill.bill_date, Date) >= from_date)
    if to_date:
        q = q.filter(func.cast(Bill.bill_date, Date) <= to_date)
    return q.order_by(Bill.bill_date.desc()).limit(200).all()


@router.get("/bills/{bill_id}", response_model=BillResponse)
async def get_bill(bill_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.put("/bills/{bill_id}", response_model=BillResponse)
async def update_bill(bill_id: int, data: BillUpdate,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bill, field, value)
    calculate_bill_totals(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.post("/bills/{bill_id}/add-item", response_model=BillResponse)
async def add_bill_item(bill_id: int, item_data: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    item = BillItem(**item_data, bill_id=bill_id)
    db.add(item)
    db.flush()
    db.refresh(bill)
    calculate_bill_totals(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.post("/bills/discount-approval")
async def approve_discount(data: DiscountApproval,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == data.bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if data.discount_percent is not None:
        bill.discount_percent = data.discount_percent
    if data.discount_amount is not None:
        bill.discount_amount = data.discount_amount
    bill.discount_reason = data.discount_reason
    bill.discount_approved_by = current_user.id
    calculate_bill_totals(bill)
    db.commit()
    return {"message": "Discount applied", "bill_id": bill.id, "gross_total": bill.gross_total}


# ── PAYMENTS ──────────────────────────────────────────
@router.post("/payments", response_model=PaymentResponse, status_code=201)
async def record_payment(data: PaymentCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == data.bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    payment_data = data.model_dump()
    payment_data["received_by"] = current_user.id

    attempt_base = next_sequence_number(db, Payment)
    payment = None
    last_error = None
    for i in range(MAX_RETRIES):
        payment_data["payment_number"] = f"PAY{attempt_base + i:08d}"
        payment = Payment(**payment_data)
        db.add(payment)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            payment = None
    if last_error:
        raise last_error

    bill.paid_amount += data.amount
    bill.balance_amount = round(bill.patient_liability - bill.paid_amount, 2)
    if bill.balance_amount <= 0:
        bill.status = BillStatus.PAID
    elif bill.paid_amount > 0:
        bill.status = BillStatus.PARTIAL
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/payments/{bill_id}", response_model=list[PaymentResponse])
async def get_payments(bill_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return db.query(Payment).filter(Payment.bill_id == bill_id).all()


# ── ADVANCE PAYMENT ───────────────────────────────────
@router.post("/advance", status_code=201)
async def collect_advance(data: AdvancePaymentCreate,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    advance_data = data.model_dump()
    advance_data["balance_remaining"] = data.amount
    advance_data["received_by"] = current_user.id

    attempt_base = next_sequence_number(db, AdvancePayment)
    advance = None
    last_error = None
    for i in range(MAX_RETRIES):
        advance_data["receipt_number"] = f"ADV{attempt_base + i:07d}"
        advance = AdvancePayment(**advance_data)
        db.add(advance)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            advance = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(advance)
    return {"receipt_number": advance.receipt_number, "amount": advance.amount,
            "patient_id": advance.patient_id}


@router.get("/advance/{patient_id}")
async def get_advances(patient_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    advances = db.query(AdvancePayment).filter(
        AdvancePayment.patient_id == patient_id,
        AdvancePayment.is_adjusted == False
    ).all()
    total = sum(a.balance_remaining or 0 for a in advances)
    return {"patient_id": patient_id, "total_advance": total, "advances": [
        {"id": a.id, "receipt_number": a.receipt_number,
         "amount": a.amount, "balance_remaining": a.balance_remaining,
         "created_at": a.created_at} for a in advances
    ]}


# ── REPORTS ───────────────────────────────────────────
@router.get("/reports/daily")
async def daily_collection_report(report_date: Optional[date] = Query(None),
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    target = report_date or date.today()
    payments = db.query(Payment).filter(
        func.cast(Payment.payment_date, Date) == target).all()
    by_mode: dict = {}
    total = 0.0
    for p in payments:
        mode = p.payment_mode.value
        by_mode[mode] = by_mode.get(mode, 0) + p.amount
        total += p.amount
    bills_today = db.query(Bill).filter(
        func.cast(Bill.bill_date, Date) == target).count()
    return {"date": target, "total_collection": round(total, 2),
            "by_payment_mode": by_mode,
            "bills_generated": bills_today,
            "transactions": len(payments)}


@router.get("/reports/outstanding")
async def outstanding_report(db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    bills = db.query(Bill).filter(
        Bill.status.in_([BillStatus.PENDING, BillStatus.PARTIAL])
    ).all()
    total_outstanding = sum(b.balance_amount for b in bills)
    return {"total_outstanding": round(total_outstanding, 2),
            "pending_bills": len(bills),
            "bills": [{"bill_number": b.bill_number, "patient_id": b.patient_id,
                       "gross_total": b.gross_total, "balance_amount": b.balance_amount,
                       "bill_date": b.bill_date} for b in bills[:50]]}


@router.get("/dashboard/stats")
async def billing_stats(db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    today = date.today()
    today_bills = db.query(Bill).filter(func.cast(Bill.bill_date, Date) == today).count()
    today_collection = db.query(func.sum(Payment.amount)).filter(
        func.cast(Payment.payment_date, Date) == today).scalar() or 0
    pending_amount = db.query(func.sum(Bill.balance_amount)).filter(
        Bill.status.in_([BillStatus.PENDING, BillStatus.PARTIAL])).scalar() or 0
    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0
    return {"today_bills": today_bills,
            "today_collection": round(today_collection, 2),
            "pending_amount": round(pending_amount, 2),
            "total_revenue": round(total_revenue, 2)}


# ── REFUND WORKFLOW (items 146-149) ─────────────────────
@router.post("/refunds", response_model=RefundRequestResponse, status_code=201)
async def request_refund(data: RefundRequestCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    payment = db.query(Payment).filter(Payment.id == data.original_payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Original payment not found")
    if data.amount > payment.amount:
        raise HTTPException(status_code=400, detail=f"Refund amount cannot exceed the original payment ({payment.amount})")

    already_refunded = db.query(func.sum(RefundRequest.amount)).filter(
        RefundRequest.original_payment_id == data.original_payment_id,
        RefundRequest.status.in_([RefundStatus.REQUESTED, RefundStatus.APPROVED]),
    ).scalar() or 0
    if already_refunded + data.amount > payment.amount:
        raise HTTPException(status_code=400,
                             detail=f"Already {already_refunded} requested/approved against this payment - cannot exceed its {payment.amount} total")

    count = db.query(RefundRequest).count() + 1
    refund = RefundRequest(**data.model_dump(), bill_id=payment.bill_id,
                            refund_number=f"REF{count:07d}", requested_by=current_user.id)
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund


@router.get("/refunds", response_model=list[RefundRequestResponse])
async def list_refunds(status: Optional[str] = Query(None), bill_id: Optional[int] = Query(None),
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(RefundRequest)
    if status:
        q = q.filter(RefundRequest.status == status)
    if bill_id:
        q = q.filter(RefundRequest.bill_id == bill_id)
    return q.order_by(RefundRequest.created_at.desc()).limit(200).all()


@router.post("/refunds/{refund_id}/approve", response_model=RefundRequestResponse)
async def approve_refund(refund_id: int, data: RefundApproval, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """
    Approval is the point where money/ledger effects actually happen: a
    negative-facing Payment row (is_refund=True) is created so the bill's
    payment history shows the refund as a real transaction (not just a
    status flip on the request), and Bill.paid_amount/balance_amount/
    refund_amount/status are all updated together so they stay consistent
    with each other - the same invariant record_payment() maintains for a
    normal payment, just running in reverse.
    """
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if refund.status != RefundStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Only a requested refund can be approved")

    original_payment = db.query(Payment).filter(Payment.id == refund.original_payment_id).first()
    bill = db.query(Bill).filter(Bill.id == refund.bill_id).first()

    attempt_base = next_sequence_number(db, Payment)
    refund_payment = None
    last_error = None
    for i in range(MAX_RETRIES):
        refund_payment = Payment(
            payment_number=f"PAY{attempt_base + i:08d}", bill_id=bill.id, patient_id=bill.patient_id,
            amount=-refund.amount, payment_mode=original_payment.payment_mode,
            notes=f"Refund for {refund.refund_number}: {refund.reason}",
            received_by=current_user.id, is_refund=True,
        )
        db.add(refund_payment)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            refund_payment = None
    if last_error:
        raise last_error

    bill.paid_amount -= refund.amount
    bill.refund_amount = (bill.refund_amount or 0) + refund.amount
    bill.balance_amount = round(bill.patient_liability - bill.paid_amount, 2)
    if bill.paid_amount <= 0:
        bill.status = BillStatus.REFUNDED
    elif bill.balance_amount > 0:
        bill.status = BillStatus.PARTIAL

    refund.status = RefundStatus.APPROVED
    refund.approved_by = current_user.id
    refund.approved_at = datetime.utcnow()
    refund.refund_payment_id = refund_payment.id

    db.commit()
    db.refresh(refund)
    return refund


@router.post("/refunds/{refund_id}/reject", response_model=RefundRequestResponse)
async def reject_refund(refund_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if refund.status != RefundStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Only a requested refund can be rejected")
    refund.status = RefundStatus.REJECTED
    refund.approved_by = current_user.id
    db.commit()
    db.refresh(refund)
    return refund


@router.post("/refunds/{refund_id}/reverse", response_model=RefundRequestResponse)
async def reverse_refund(refund_id: int, data: RefundReversal, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """
    Undoes an approved refund - puts the bill's paid_amount/balance/status
    back to where they were before the refund. Does NOT delete the
    original negative Payment row (deleting financial transaction history
    is a bad idea even when reversing it) - instead nets it out with a
    positive counter-entry, so the bill's payment list shows the full
    story: original payment, refund, reversal, each a real row.
    """
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if refund.status != RefundStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only an approved refund can be reversed")

    bill = db.query(Bill).filter(Bill.id == refund.bill_id).first()
    original_payment = db.query(Payment).filter(Payment.id == refund.original_payment_id).first()

    attempt_base = next_sequence_number(db, Payment)
    reversal_payment = None
    last_error = None
    for i in range(MAX_RETRIES):
        reversal_payment = Payment(
            payment_number=f"PAY{attempt_base + i:08d}", bill_id=bill.id, patient_id=bill.patient_id,
            amount=refund.amount, payment_mode=original_payment.payment_mode,
            notes=f"Reversal of refund {refund.refund_number}: {data.reversal_reason}",
            received_by=current_user.id,
        )
        db.add(reversal_payment)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            reversal_payment = None
    if last_error:
        raise last_error

    bill.paid_amount += refund.amount
    bill.refund_amount = max(0, (bill.refund_amount or 0) - refund.amount)
    bill.balance_amount = round(bill.patient_liability - bill.paid_amount, 2)
    if bill.balance_amount <= 0:
        bill.status = BillStatus.PAID
    elif bill.paid_amount > 0:
        bill.status = BillStatus.PARTIAL

    refund.status = RefundStatus.REVERSED
    refund.reversed_by = current_user.id
    refund.reversed_at = datetime.utcnow()
    refund.reversal_reason = data.reversal_reason

    db.commit()
    db.refresh(refund)
    return refund




