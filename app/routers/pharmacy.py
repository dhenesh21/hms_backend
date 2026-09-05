from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from typing import Optional
from datetime import datetime, date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.pharmacy import (DrugMaster, DrugStock, PharmacySupplier,
                                   PharmacyPurchaseOrder, POItem,
                                   PharmacyDispense, DispenseItem, DispenseStatus,
                                   DrugReturn, ReturnDirection, ReturnStatus,
                                   DrugTransfer, StockAdjustment)
from app.models.user import User
from app.schemas.pharmacy import (
    DrugMasterCreate, DrugMasterResponse, DrugWithStockResponse,
    DrugStockCreate, DrugStockResponse,
    SupplierCreate, SupplierResponse,
    PurchaseOrderCreate, PurchaseOrderResponse,
    DispenseCreate, DispenseResponse,
    StockAlertResponse,
    DrugReturnCreate, DrugReturnDecision, DrugReturnResponse,
    DrugTransferCreate, DrugTransferResponse,
    StockAdjustmentCreate, StockAdjustmentResponse,
    POReceiveRequest,
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


# ── DRUG MASTER ───────────────────────────────────────
@router.post("/drugs", response_model=DrugMasterResponse, status_code=201)
async def create_drug(data: DrugMasterCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    if db.query(DrugMaster).filter(DrugMaster.drug_code == data.drug_code).first():
        raise HTTPException(status_code=400, detail="Drug code already exists")
    drug = DrugMaster(**data.model_dump())
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return drug


@router.get("/drugs", response_model=list[DrugWithStockResponse])
async def list_drugs(search: Optional[str] = Query(None),
                     category: Optional[str] = Query(None),
                     low_stock: bool = Query(False),
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    q = db.query(DrugMaster).filter(DrugMaster.is_active == True)
    if search:
        q = q.filter(
            (DrugMaster.brand_name.ilike(f"%{search}%")) |
            (DrugMaster.generic_name.ilike(f"%{search}%")) |
            (DrugMaster.drug_code.ilike(f"%{search}%"))
        )
    if category:
        q = q.filter(DrugMaster.category == category)
    drugs = q.all()
    result = []
    for drug in drugs:
        active_stock = [s for s in drug.stock_batches if s.is_active and s.expiry_date >= date.today()]
        total = sum(s.quantity_available for s in active_stock)
        if low_stock and total > drug.reorder_level:
            continue
        nearest = min((s.expiry_date for s in active_stock), default=None)
        result.append(DrugWithStockResponse(
            id=drug.id, drug_code=drug.drug_code, brand_name=drug.brand_name,
            generic_name=drug.generic_name, category=drug.category,
            formulation=drug.formulation, strength=drug.strength, unit=drug.unit,
            total_stock=total, reorder_level=drug.reorder_level,
            is_low_stock=total <= drug.reorder_level, nearest_expiry=nearest
        ))
    return result


@router.get("/drugs/{drug_id}/stock", response_model=list[DrugStockResponse])
async def get_drug_stock(drug_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(DrugStock).filter(
        DrugStock.drug_id == drug_id, DrugStock.is_active == True
    ).order_by(DrugStock.expiry_date.asc()).all()


# ── STOCK INTAKE ──────────────────────────────────────
@router.post("/stock", response_model=DrugStockResponse, status_code=201)
async def add_stock(data: DrugStockCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    if not db.query(DrugMaster).filter(DrugMaster.id == data.drug_id).first():
        raise HTTPException(status_code=404, detail="Drug not found")
    stock = DrugStock(**data.model_dump(), quantity_available=data.quantity_received,
                      received_by=current_user.id)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


# ── SUPPLIERS ─────────────────────────────────────────
@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(data: SupplierCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    supplier = PharmacySupplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/suppliers", response_model=list[SupplierResponse])
async def list_suppliers(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(PharmacySupplier).filter(PharmacySupplier.is_active == True).all()


# ── PURCHASE ORDERS ───────────────────────────────────
@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=201)
async def create_po(data: PurchaseOrderCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    from sqlalchemy.exc import IntegrityError

    total = sum(i.quantity_ordered * i.unit_price for i in data.items)

    attempt_base = next_sequence_number(db, PharmacyPurchaseOrder)
    po = None
    last_error = None
    for i in range(MAX_RETRIES):
        po = PharmacyPurchaseOrder(
            po_number=f"PO{attempt_base + i:06d}", supplier_id=data.supplier_id,
            expected_delivery=data.expected_delivery, notes=data.notes,
            total_amount=total, created_by=current_user.id
        )
        db.add(po)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            po = None
    if last_error:
        raise last_error

    for item in data.items:
        po_item = POItem(purchase_order_id=po.id, drug_id=item.drug_id,
                         quantity_ordered=item.quantity_ordered,
                         unit_price=item.unit_price,
                         total_price=item.quantity_ordered * item.unit_price)
        db.add(po_item)
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse])
async def list_pos(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    return db.query(PharmacyPurchaseOrder).order_by(
        PharmacyPurchaseOrder.created_at.desc()).limit(100).all()


@router.put("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_po(po_id: int, data: POReceiveRequest, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """
    Item 107 (real GRN) — previously this just flipped PO status to
    "received" without creating any stock. Now: for each item actually
    received (batch/expiry/pricing supplied per line, since different
    lines can arrive in different batches), creates the DrugStock row,
    increments POItem.quantity_received, and only marks the PO "received"
    once every item's quantity_received reaches quantity_ordered —
    otherwise "partial", matching the status values the model already
    declared but that were never actually being set differently before.
    """
    po = db.query(PharmacyPurchaseOrder).filter(PharmacyPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    if po.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot receive a cancelled PO")

    for line in data.items:
        po_item = db.query(POItem).filter(
            POItem.id == line.po_item_id, POItem.purchase_order_id == po_id).first()
        if not po_item:
            raise HTTPException(status_code=404, detail=f"PO item {line.po_item_id} not found on this PO")
        remaining = po_item.quantity_ordered - po_item.quantity_received
        if line.quantity_received > remaining:
            raise HTTPException(status_code=400,
                                 detail=f"Cannot receive {line.quantity_received} for PO item {line.po_item_id} - only {remaining} remaining")

        stock = DrugStock(
            drug_id=po_item.drug_id, batch_number=line.batch_number,
            expiry_date=line.expiry_date, manufacture_date=line.manufacture_date,
            quantity_received=line.quantity_received, quantity_available=line.quantity_received,
            purchase_price=po_item.unit_price, sale_price=line.sale_price, mrp=line.mrp,
            supplier_id=po.supplier_id, purchase_order_id=po.id,
            location=line.location, received_by=current_user.id,
        )
        db.add(stock)
        po_item.quantity_received += line.quantity_received

    db.flush()
    all_items = db.query(POItem).filter(POItem.purchase_order_id == po_id).all()
    if all(i.quantity_received >= i.quantity_ordered for i in all_items):
        po.status = "received"
    elif any(i.quantity_received > 0 for i in all_items):
        po.status = "partial"

    db.commit()
    db.refresh(po)
    return po



# ── DISPENSING ────────────────────────────────────────
@router.post("/dispense", response_model=DispenseResponse, status_code=201)
async def dispense_medicines(data: DispenseCreate, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    from sqlalchemy.exc import IntegrityError

    attempt_base = next_sequence_number(db, PharmacyDispense)
    dispense = None
    last_error = None
    for i in range(MAX_RETRIES):
        dispense = PharmacyDispense(
            dispense_number=f"DISP{attempt_base + i:07d}",
            patient_id=data.patient_id,
            prescription_source=data.prescription_source,
            opd_visit_id=data.opd_visit_id,
            ipd_admission_id=data.ipd_admission_id,
            payment_mode=data.payment_mode,
            notes=data.notes,
            dispensed_by=current_user.id
        )
        db.add(dispense)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            dispense = None
    if last_error:
        raise last_error

    total = 0.0
    tax_total = 0.0
    discount_total = 0.0

    for item_data in data.items:
        # Find FEFO batch (First Expiry First Out)
        stock = db.query(DrugStock).filter(
            DrugStock.drug_id == item_data.drug_id,
            DrugStock.quantity_available >= item_data.quantity,
            DrugStock.is_active == True,
            DrugStock.expiry_date > date.today()
        ).order_by(DrugStock.expiry_date.asc()).first()

        item_total = item_data.quantity * item_data.unit_price
        discount = item_total * (item_data.discount_percent / 100)
        tax = (item_total - discount) * (item_data.tax_percent / 100)
        net = item_total - discount + tax

        di = DispenseItem(
            dispense_id=dispense.id,
            drug_id=item_data.drug_id,
            stock_id=stock.id if stock else None,
            drug_name=item_data.drug_name,
            batch_number=stock.batch_number if stock else None,
            expiry_date=stock.expiry_date if stock else None,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            tax_percent=item_data.tax_percent,
            tax_amount=round(tax, 2),
            discount_percent=item_data.discount_percent,
            discount_amount=round(discount, 2),
            total_price=round(net, 2),
            dosage_instructions=item_data.dosage_instructions
        )
        db.add(di)

        # Deduct stock
        if stock:
            stock.quantity_available -= item_data.quantity

        total += item_total
        tax_total += tax
        discount_total += discount

    dispense.total_amount = round(total, 2)
    dispense.tax_amount = round(tax_total, 2)
    dispense.discount_amount = round(discount_total, 2)
    dispense.net_amount = round(total + tax_total - discount_total, 2)
    dispense.status = DispenseStatus.DISPENSED

    db.commit()
    db.refresh(dispense)
    return dispense


@router.get("/dispense", response_model=list[DispenseResponse])
async def list_dispenses(patient_id: Optional[int] = Query(None),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(PharmacyDispense)
    if patient_id:
        q = q.filter(PharmacyDispense.patient_id == patient_id)
    return q.order_by(PharmacyDispense.created_at.desc()).limit(100).all()


# ── STOCK ALERTS ──────────────────────────────────────
@router.get("/alerts", response_model=list[StockAlertResponse])
async def get_stock_alerts(db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    alerts = []
    drugs = db.query(DrugMaster).filter(DrugMaster.is_active == True).all()
    warning_days = 90

    for drug in drugs:
        active_stock = [s for s in drug.stock_batches if s.is_active]
        total = sum(s.quantity_available for s in active_stock)
        nearest = min((s.expiry_date for s in active_stock if s.quantity_available > 0), default=None)

        if total == 0:
            alerts.append(StockAlertResponse(
                drug_id=drug.id, drug_code=drug.drug_code,
                brand_name=drug.brand_name, generic_name=drug.generic_name,
                alert_type="out_of_stock", current_stock=0,
                reorder_level=drug.reorder_level,
                nearest_expiry=nearest, days_to_expiry=None
            ))
        elif total <= drug.reorder_level:
            alerts.append(StockAlertResponse(
                drug_id=drug.id, drug_code=drug.drug_code,
                brand_name=drug.brand_name, generic_name=drug.generic_name,
                alert_type="low_stock", current_stock=total,
                reorder_level=drug.reorder_level,
                nearest_expiry=nearest, days_to_expiry=None
            ))

        if nearest:
            days = (nearest - date.today()).days
            if days <= warning_days:
                alerts.append(StockAlertResponse(
                    drug_id=drug.id, drug_code=drug.drug_code,
                    brand_name=drug.brand_name, generic_name=drug.generic_name,
                    alert_type="expired" if days < 0 else "expiring_soon",
                    current_stock=total, reorder_level=drug.reorder_level,
                    nearest_expiry=nearest, days_to_expiry=days
                ))
    return alerts


@router.get("/dashboard/stats")
async def pharmacy_stats(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    today = date.today()
    total_drugs = db.query(DrugMaster).filter(DrugMaster.is_active == True).count()
    low_stock = sum(1 for d in db.query(DrugMaster).filter(DrugMaster.is_active == True).all()
                    if sum(s.quantity_available for s in d.stock_batches if s.is_active) <= d.reorder_level)
    expiring = db.query(DrugStock).filter(
        DrugStock.expiry_date <= today + timedelta(days=90),
        DrugStock.expiry_date >= today,
        DrugStock.quantity_available > 0,
        DrugStock.is_active == True
    ).count()
    today_dispense = db.query(PharmacyDispense).filter(
        func.cast(PharmacyDispense.created_at, Date) == today).count()
    today_revenue = db.query(func.sum(PharmacyDispense.net_amount)).filter(
        func.cast(PharmacyDispense.created_at, Date) == today).scalar() or 0
    return {"total_drugs": total_drugs, "low_stock_count": low_stock,
            "expiring_soon": expiring, "today_dispense": today_dispense,
            "today_revenue": round(today_revenue, 2)}


# ── DRUG RETURN (item 101) ──────────────────────────────
@router.post("/returns", response_model=DrugReturnResponse, status_code=201)
async def request_return(data: DrugReturnCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    if data.direction == ReturnDirection.FROM_PATIENT.value and not data.dispense_item_id:
        raise HTTPException(status_code=400, detail="dispense_item_id is required for a patient return")
    if data.direction == ReturnDirection.TO_SUPPLIER.value and not data.supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id is required for a to-supplier return")

    count = db.query(DrugReturn).count() + 1
    ret = DrugReturn(**data.model_dump(), return_number=f"RET{count:07d}", requested_by=current_user.id)
    db.add(ret)
    db.commit()
    db.refresh(ret)
    return ret


@router.get("/returns", response_model=list[DrugReturnResponse])
async def list_returns(status: Optional[str] = Query(None), db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    q = db.query(DrugReturn)
    if status:
        q = q.filter(DrugReturn.status == status)
    return q.order_by(DrugReturn.created_at.desc()).limit(200).all()


@router.post("/returns/{return_id}/approve", response_model=DrugReturnResponse)
async def approve_return(return_id: int, data: DrugReturnDecision, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """
    Approving actually moves stock, not just a status flip: a
    FROM_PATIENT return puts quantity back into the originating batch
    (only if that batch hasn't expired - returned expired medicine gets
    approved into the record for tracking but doesn't re-enter sellable
    stock); a TO_SUPPLIER return decrements the batch it came from.
    """
    ret = db.query(DrugReturn).filter(DrugReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    if ret.status != ReturnStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Only a requested return can be approved")

    if ret.stock_id:
        stock = db.query(DrugStock).filter(DrugStock.id == ret.stock_id).first()
        if stock:
            if ret.direction == ReturnDirection.FROM_PATIENT and stock.expiry_date >= date.today():
                stock.quantity_available += ret.quantity
            elif ret.direction == ReturnDirection.TO_SUPPLIER:
                stock.quantity_available = max(0, stock.quantity_available - ret.quantity)

    ret.status = ReturnStatus.APPROVED
    ret.approved_by = current_user.id
    db.commit()
    db.refresh(ret)
    return ret


@router.post("/returns/{return_id}/reject", response_model=DrugReturnResponse)
async def reject_return(return_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    ret = db.query(DrugReturn).filter(DrugReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    ret.status = ReturnStatus.REJECTED
    ret.approved_by = current_user.id
    db.commit()
    db.refresh(ret)
    return ret


# ── DRUG TRANSFER (item 102) ────────────────────────────
@router.post("/transfers", response_model=DrugTransferResponse, status_code=201)
async def transfer_stock(data: DrugTransferCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    stock = db.query(DrugStock).filter(DrugStock.id == data.stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock batch not found")
    if data.quantity > stock.quantity_available:
        raise HTTPException(status_code=400, detail=f"Only {stock.quantity_available} available in this batch")

    count = db.query(DrugTransfer).count() + 1
    transfer = DrugTransfer(**data.model_dump(), transfer_number=f"TRF{count:07d}",
                             from_location=stock.location, transferred_by=current_user.id)
    db.add(transfer)

    # Moving location on the same batch row for a same-branch transfer; a
    # cross-branch transfer instead splits into a new batch row at the
    # destination so DrugStock.location stays a true per-row physical spot.
    if data.to_branch_id and data.to_branch_id != data.from_branch_id:
        stock.quantity_available -= data.quantity
        db.add(DrugStock(
            drug_id=stock.drug_id, batch_number=stock.batch_number, expiry_date=stock.expiry_date,
            manufacture_date=stock.manufacture_date, quantity_received=data.quantity,
            quantity_available=data.quantity, purchase_price=stock.purchase_price,
            sale_price=stock.sale_price, mrp=stock.mrp, supplier_id=stock.supplier_id,
            location=data.to_location, received_by=current_user.id,
        ))
    else:
        stock.location = data.to_location

    db.commit()
    db.refresh(transfer)
    return transfer


@router.get("/transfers", response_model=list[DrugTransferResponse])
async def list_transfers(stock_id: Optional[int] = Query(None), db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(DrugTransfer)
    if stock_id:
        q = q.filter(DrugTransfer.stock_id == stock_id)
    return q.order_by(DrugTransfer.created_at.desc()).limit(200).all()


# ── STOCK ADJUSTMENT (item 103) ─────────────────────────
@router.post("/stock-adjustments", response_model=StockAdjustmentResponse, status_code=201)
async def adjust_stock(data: StockAdjustmentCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    stock = db.query(DrugStock).filter(DrugStock.id == data.stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock batch not found")
    if data.new_quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    adjustment = StockAdjustment(
        stock_id=data.stock_id, reason=data.reason,
        quantity_before=stock.quantity_available, quantity_after=data.new_quantity,
        notes=data.notes, adjusted_by=current_user.id,
    )
    db.add(adjustment)
    stock.quantity_available = data.new_quantity
    if data.reason == "expiry_write_off":
        stock.is_active = False

    db.commit()
    db.refresh(adjustment)
    return adjustment


@router.get("/stock-adjustments", response_model=list[StockAdjustmentResponse])
async def list_adjustments(stock_id: Optional[int] = Query(None), db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    q = db.query(StockAdjustment)
    if stock_id:
        q = q.filter(StockAdjustment.stock_id == stock_id)
    return q.order_by(StockAdjustment.created_at.desc()).limit(200).all()




