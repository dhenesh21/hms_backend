from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.inventory import (
    InventoryItem,
    InventoryVendor,
    InventoryPurchaseOrder,
    InventoryPOItem,
    InventoryGRN,
    InventoryGRNItem,
    InventoryStock,
    InventoryMovement,
    POStatus,
    MovementType,
)
from app.models.user import User
from app.schemas.inventory import (
    ItemCreate,
    ItemResponse,
    VendorCreate,
    VendorResponse,
    POCreate,
    POResponse,
    GRNCreate,
    GRNResponse,
    StockResponse,
    MovementCreate,
    MovementResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ── ITEMS ─────────────────────────────────────────────

@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(InventoryItem).filter(InventoryItem.item_code == data.item_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="An item with this code already exists")
    item = InventoryItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InventoryItem)
    if active_only:
        q = q.filter(InventoryItem.is_active == True)  # noqa: E712
    return q.order_by(InventoryItem.name).all()


# ── VENDORS ─────────────────────────────────────────────

@router.post("/vendors", response_model=VendorResponse, status_code=201)
async def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = InventoryVendor(**data.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors", response_model=list[VendorResponse])
async def list_vendors(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InventoryVendor)
    if active_only:
        q = q.filter(InventoryVendor.is_active == True)  # noqa: E712
    return q.order_by(InventoryVendor.name).all()


# ── PURCHASE ORDERS ─────────────────────────────────────────────

@router.post("/purchase-orders", response_model=POResponse, status_code=201)
async def create_po(
    data: POCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = db.query(InventoryVendor).filter(InventoryVendor.id == data.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not data.items:
        raise HTTPException(status_code=400, detail="Purchase order must have at least one item")

    items_data = data.items
    po_data = data.model_dump(exclude={"items"})
    po_data["created_by"] = current_user.id

    attempt_base = next_sequence_number(db, InventoryPurchaseOrder)
    po = None
    last_error = None
    for i in range(MAX_RETRIES):
        po_data["po_number"] = f"PO{attempt_base + i:06d}"
        po = InventoryPurchaseOrder(**po_data)
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

    for item_data in items_data:
        item = db.query(InventoryItem).filter(InventoryItem.id == item_data.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {item_data.item_id} not found")
        po_item = InventoryPOItem(**item_data.model_dump(), po_id=po.id)
        db.add(po_item)

    po.status = POStatus.SENT
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders", response_model=list[POResponse])
async def list_pos(
    status: Optional[POStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InventoryPurchaseOrder)
    if status:
        q = q.filter(InventoryPurchaseOrder.status == status)
    return q.order_by(InventoryPurchaseOrder.order_date.desc()).all()


@router.get("/purchase-orders/{po_id}", response_model=POResponse)
async def get_po(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = db.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


# ── GRN (GOODS RECEIPT) ─────────────────────────────────────────────

@router.post("/grn", response_model=GRNResponse, status_code=201)
async def receive_grn(
    data: GRNCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = db.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.id == data.po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status in (POStatus.RECEIVED, POStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot receive against a PO with status '{po.status.value}'")
    if not data.items:
        raise HTTPException(status_code=400, detail="GRN must have at least one item")

    items_data = data.items
    grn_data = data.model_dump(exclude={"items"})
    grn_data["received_by"] = current_user.id

    attempt_base = next_sequence_number(db, InventoryGRN)
    grn = None
    last_error = None
    for i in range(MAX_RETRIES):
        grn_data["grn_number"] = f"GRN{attempt_base + i:06d}"
        grn = InventoryGRN(**grn_data)
        db.add(grn)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            grn = None
    if last_error:
        raise last_error

    for item_data in items_data:
        po_item = db.query(InventoryPOItem).filter(InventoryPOItem.id == item_data.po_item_id, InventoryPOItem.po_id == po.id).first()
        if not po_item:
            raise HTTPException(status_code=404, detail=f"PO item {item_data.po_item_id} not found on this PO")

        remaining = po_item.quantity_ordered - po_item.quantity_received
        if item_data.quantity_received > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive {item_data.quantity_received} - only {remaining} remaining on PO item {po_item.id}",
            )

        grn_item = InventoryGRNItem(**item_data.model_dump(), grn_id=grn.id)
        db.add(grn_item)

        po_item.quantity_received += item_data.quantity_received

        stock = (
            db.query(InventoryStock)
            .filter(InventoryStock.item_id == item_data.item_id, InventoryStock.location == "Central Store")
            .first()
        )
        if not stock:
            stock = InventoryStock(item_id=item_data.item_id, location="Central Store", quantity_available=0)
            db.add(stock)
            db.flush()
        stock.quantity_available += item_data.quantity_received

    db.flush()
    all_items = db.query(InventoryPOItem).filter(InventoryPOItem.po_id == po.id).all()
    if all(i.quantity_received >= i.quantity_ordered for i in all_items):
        po.status = POStatus.RECEIVED
    else:
        po.status = POStatus.PARTIALLY_RECEIVED

    db.commit()
    db.refresh(grn)
    return grn


# ── STOCK ─────────────────────────────────────────────

@router.get("/stock", response_model=list[StockResponse])
async def list_stock(
    item_id: Optional[int] = Query(None),
    low_stock_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InventoryStock)
    if item_id:
        q = q.filter(InventoryStock.item_id == item_id)
    results = q.all()
    if low_stock_only:
        results = [s for s in results if s.item and s.quantity_available <= s.item.reorder_level]
    return results


# ── MOVEMENTS (ISSUE / TRANSFER / RETURN / ADJUSTMENT) ─────────────────────────────────────────────

@router.post("/movements", response_model=MovementResponse, status_code=201)
async def record_movement(
    data: MovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(InventoryItem).filter(InventoryItem.id == data.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if data.movement_type in (MovementType.ISSUE, MovementType.TRANSFER):
        location = data.from_location or "Central Store"
        stock = db.query(InventoryStock).filter(InventoryStock.item_id == data.item_id, InventoryStock.location == location).first()
        if not stock or stock.quantity_available < data.quantity:
            available = stock.quantity_available if stock else 0
            raise HTTPException(status_code=400, detail=f"Insufficient stock at {location}: {available} available, {data.quantity} requested")
        stock.quantity_available -= data.quantity

        if data.movement_type == MovementType.TRANSFER and data.to_location:
            dest_stock = db.query(InventoryStock).filter(InventoryStock.item_id == data.item_id, InventoryStock.location == data.to_location).first()
            if not dest_stock:
                dest_stock = InventoryStock(item_id=data.item_id, location=data.to_location, quantity_available=0)
                db.add(dest_stock)
                db.flush()
            dest_stock.quantity_available += data.quantity

    elif data.movement_type == MovementType.RETURN:
        location = data.to_location or "Central Store"
        stock = db.query(InventoryStock).filter(InventoryStock.item_id == data.item_id, InventoryStock.location == location).first()
        if not stock:
            stock = InventoryStock(item_id=data.item_id, location=location, quantity_available=0)
            db.add(stock)
            db.flush()
        stock.quantity_available += data.quantity

    elif data.movement_type == MovementType.ADJUSTMENT:
        location = data.to_location or data.from_location or "Central Store"
        stock = db.query(InventoryStock).filter(InventoryStock.item_id == data.item_id, InventoryStock.location == location).first()
        if not stock:
            stock = InventoryStock(item_id=data.item_id, location=location, quantity_available=0)
            db.add(stock)
            db.flush()
        new_qty = stock.quantity_available + data.quantity
        if new_qty < 0:
            raise HTTPException(status_code=400, detail="Adjustment would result in negative stock")
        stock.quantity_available = new_qty

    movement = InventoryMovement(**data.model_dump(), moved_by=current_user.id)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.get("/movements", response_model=list[MovementResponse])
async def list_movements(
    item_id: Optional[int] = Query(None),
    movement_type: Optional[MovementType] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(InventoryMovement)
    if item_id:
        q = q.filter(InventoryMovement.item_id == item_id)
    if movement_type:
        q = q.filter(InventoryMovement.movement_type == movement_type)
    return q.order_by(InventoryMovement.moved_at.desc()).limit(limit).all()


# ── DASHBOARD ─────────────────────────────────────────────

@router.get("/dashboard/stats")
async def inventory_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_items = db.query(InventoryItem).filter(InventoryItem.is_active == True).count()  # noqa: E712
    open_pos = db.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.status.in_([POStatus.SENT, POStatus.PARTIALLY_RECEIVED])).count()

    all_stock = db.query(InventoryStock).all()
    low_stock_count = sum(1 for s in all_stock if s.item and s.quantity_available <= s.item.reorder_level)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    movements_today = db.query(InventoryMovement).filter(InventoryMovement.moved_at >= today_start).count()

    return {
        "total_items": total_items,
        "open_purchase_orders": open_pos,
        "low_stock_items": low_stock_count,
        "movements_today": movements_today,
    }
