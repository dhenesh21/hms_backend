from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class ItemCategory(str, enum.Enum):
    CONSUMABLE = "consumable"
    ASSET = "asset"
    STATIONERY = "stationery"
    GENERAL = "general"


class POStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class MovementType(str, enum.Enum):
    ISSUE = "issue"
    TRANSFER = "transfer"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(Enum(ItemCategory), default=ItemCategory.CONSUMABLE)
    unit = Column(String(30), default="piece")
    reorder_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock_entries = relationship("InventoryStock", back_populates="item")


class InventoryVendor(Base):
    __tablename__ = "inventory_vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryPurchaseOrder(Base):
    __tablename__ = "inventory_purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(20), unique=True, index=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("inventory_vendors.id"), nullable=False)
    status = Column(Enum(POStatus), default=POStatus.DRAFT)

    order_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_delivery_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("InventoryPOItem", back_populates="purchase_order")


class InventoryPOItem(Base):
    __tablename__ = "inventory_po_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("inventory_purchase_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_price = Column(Float, nullable=False)

    purchase_order = relationship("InventoryPurchaseOrder", back_populates="items")


class InventoryGRN(Base):
    __tablename__ = "inventory_grn"

    id = Column(Integer, primary_key=True, index=True)
    grn_number = Column(String(20), unique=True, index=True, nullable=False)
    po_id = Column(Integer, ForeignKey("inventory_purchase_orders.id"), nullable=False)

    received_date = Column(DateTime(timezone=True), server_default=func.now())
    received_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    items = relationship("InventoryGRNItem", back_populates="grn")


class InventoryGRNItem(Base):
    __tablename__ = "inventory_grn_items"

    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("inventory_grn.id"), nullable=False)
    po_item_id = Column(Integer, ForeignKey("inventory_po_items.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_received = Column(Integer, nullable=False)

    grn = relationship("InventoryGRN", back_populates="items")


class InventoryStock(Base):
    __tablename__ = "inventory_stock"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    location = Column(String(100), default="Central Store")
    quantity_available = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    item = relationship("InventoryItem", back_populates="stock_entries")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    movement_type = Column(Enum(MovementType), nullable=False)

    quantity = Column(Integer, nullable=False)
    from_location = Column(String(100), nullable=True)
    to_location = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    reason = Column(Text, nullable=True)
    moved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    moved_at = Column(DateTime(timezone=True), server_default=func.now())
