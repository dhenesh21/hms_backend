from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DrugCategory(str, enum.Enum):
    ANTIBIOTIC = "antibiotic"
    ANALGESIC = "analgesic"
    ANTIHYPERTENSIVE = "antihypertensive"
    ANTIDIABETIC = "antidiabetic"
    ANTIFUNGAL = "antifungal"
    ANTIVIRAL = "antiviral"
    CARDIOVASCULAR = "cardiovascular"
    GASTROINTESTINAL = "gastrointestinal"
    RESPIRATORY = "respiratory"
    NEUROLOGICAL = "neurological"
    HORMONAL = "hormonal"
    VITAMIN = "vitamin"
    VACCINE = "vaccine"
    SURGICAL = "surgical"
    IV_FLUID = "iv_fluid"
    OTHER = "other"


class DrugFormulation(str, enum.Enum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    INJECTION = "injection"
    CREAM = "cream"
    OINTMENT = "ointment"
    DROPS = "drops"
    INHALER = "inhaler"
    PATCH = "patch"
    SUPPOSITORY = "suppository"
    POWDER = "powder"
    IV_SOLUTION = "iv_solution"


class DispenseStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class DrugMaster(Base):
    """Master drug catalogue"""
    __tablename__ = "drug_master"

    id = Column(Integer, primary_key=True, index=True)
    drug_code = Column(String(20), unique=True, nullable=False, index=True)
    brand_name = Column(String(200), nullable=False)
    generic_name = Column(String(200), nullable=False)
    category = Column(Enum(DrugCategory), nullable=False)
    formulation = Column(Enum(DrugFormulation), nullable=False)
    strength = Column(String(100))        # e.g. "500mg", "10mg/5ml"
    unit = Column(String(50))             # tablet, ml, vial
    manufacturer = Column(String(200))
    schedule = Column(String(10))         # H, H1, G, X (Schedule H drug)
    is_narcotic = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    hsn_code = Column(String(20))
    tax_percent = Column(Float, default=12.0)
    reorder_level = Column(Integer, default=10)
    # Item 93 — the fields the checklist flagged as missing. Free-text
    # rather than a structured interaction-pair table: a real interaction
    # DATABASE (which drug conflicts with which) is a licensed data source
    # (FDB/Lexicomp/RxNorm) exactly like Group 5's Terminology Repository
    # flagged for ICD/LOINC/SNOMED — fabricating one here would be actively
    # dangerous in a clinical system. What's added is where a pharmacist
    # can record known interactions/contraindications for THIS drug so
    # they're visible on the drug record; Group 4's CDS rule engine
    # (models/cds.py) is the actual keyword-matching mechanism that acts on
    # this kind of data at order time.
    known_interactions = Column(Text, nullable=True)
    contraindications = Column(Text, nullable=True)
    pregnancy_category = Column(String(10), nullable=True)   # A, B, C, D, X
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock_batches = relationship("DrugStock", back_populates="drug")


class DrugStock(Base):
    """Each batch of drug in inventory"""
    __tablename__ = "drug_stock"

    id = Column(Integer, primary_key=True, index=True)
    drug_id = Column(Integer, ForeignKey("drug_master.id"), nullable=False)
    batch_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False)
    manufacture_date = Column(Date)
    quantity_received = Column(Integer, nullable=False)
    quantity_available = Column(Integer, nullable=False)
    purchase_price = Column(Float, nullable=False)    # per unit
    sale_price = Column(Float, nullable=False)        # MRP per unit
    mrp = Column(Float)
    supplier_id = Column(Integer, ForeignKey("pharmacy_suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("pharmacy_purchase_orders.id"), nullable=True)
    location = Column(String(100))    # shelf location in pharmacy
    is_active = Column(Boolean, default=True)
    received_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    drug = relationship("DrugMaster", back_populates="stock_batches")


class PharmacySupplier(Base):
    __tablename__ = "pharmacy_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    contact_person = Column(String(200))
    phone = Column(String(20))
    email = Column(String(200))
    address = Column(Text)
    gst_number = Column(String(20))
    drug_license_number = Column(String(100))
    payment_terms = Column(String(100))  # Net 30, COD etc
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PharmacyPurchaseOrder(Base):
    __tablename__ = "pharmacy_purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(20), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("pharmacy_suppliers.id"), nullable=False)
    order_date = Column(Date, server_default=func.current_date())
    expected_delivery = Column(Date)
    status = Column(String(20), default="pending")  # pending, partial, received, cancelled
    total_amount = Column(Float, default=0.0)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("PharmacySupplier")
    items = relationship("POItem", back_populates="purchase_order")


class POItem(Base):
    __tablename__ = "po_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("pharmacy_purchase_orders.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drug_master.id"), nullable=False)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PharmacyPurchaseOrder", back_populates="items")


class PharmacyDispense(Base):
    """Prescription dispensing record"""
    __tablename__ = "pharmacy_dispense"

    id = Column(Integer, primary_key=True, index=True)
    dispense_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    prescription_source = Column(String(20), default="opd")  # opd, ipd, external
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    status = Column(Enum(DispenseStatus), default=DispenseStatus.PENDING)
    total_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    net_amount = Column(Float, default=0.0)
    payment_mode = Column(String(50))
    is_paid = Column(Boolean, default=False)
    dispensed_by = Column(Integer, ForeignKey("users.id"))
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("DispenseItem", back_populates="dispense")


class ReturnDirection(str, enum.Enum):
    TO_SUPPLIER = "to_supplier"        # damaged/expired stock sent back to vendor
    FROM_PATIENT = "from_patient"      # dispensed medicine returned unused


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DrugReturn(Base):
    """
    Item 101 (Drug Return). Two genuinely different flows share this table
    (direction distinguishes them) rather than being two separate tables,
    since both are "stock leaves/re-enters through a return", just with a
    different counterparty:
    - TO_SUPPLIER: damaged/expired/recalled stock sent back — decrements
      DrugStock, does not affect any dispense record.
    - FROM_PATIENT: an unused dispensed item returned by a patient — links
      back to the original DispenseItem and, on approval, increments
      DrugStock.quantity_available for that batch again (if not expired).
    """
    __tablename__ = "drug_returns"

    id = Column(Integer, primary_key=True, index=True)
    return_number = Column(String(20), unique=True, nullable=False)
    direction = Column(Enum(ReturnDirection), nullable=False)
    status = Column(Enum(ReturnStatus), default=ReturnStatus.REQUESTED)

    drug_id = Column(Integer, ForeignKey("drug_master.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("drug_stock.id"), nullable=True)
    dispense_item_id = Column(Integer, ForeignKey("dispense_items.id"), nullable=True)   # set for FROM_PATIENT
    supplier_id = Column(Integer, ForeignKey("pharmacy_suppliers.id"), nullable=True)     # set for TO_SUPPLIER

    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class DrugTransfer(Base):
    """
    Item 102 (Drug Transfer) — moving stock between locations (e.g. main
    pharmacy store to a ward sub-store, or between branches once a hospital
    has more than one — see organization.Branch). Deliberately references
    `DrugStock.location` (a free-text shelf/location field that already
    existed) as the from/to rather than inventing a separate location
    master here — keeps this additive to what's already in the schema.
    """
    __tablename__ = "drug_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_number = Column(String(20), unique=True, nullable=False)
    stock_id = Column(Integer, ForeignKey("drug_stock.id"), nullable=False)
    from_location = Column(String(100), nullable=True)
    to_location = Column(String(100), nullable=False)
    from_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    to_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdjustmentReason(str, enum.Enum):
    DAMAGE = "damage"
    WASTAGE = "wastage"
    THEFT_LOSS = "theft_loss"
    EXPIRY_WRITE_OFF = "expiry_write_off"
    STOCK_COUNT_CORRECTION = "stock_count_correction"


class StockAdjustment(Base):
    """
    Item 103 (Stock Adjustment) — any manual correction to
    DrugStock.quantity_available that isn't a normal dispense/return/
    transfer. Always logged with before/after quantities and a reason,
    since silently changing stock numbers without an audit trail is
    exactly the kind of gap that makes inventory numbers untrustworthy.
    """
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("drug_stock.id"), nullable=False)
    reason = Column(Enum(AdjustmentReason), nullable=False)
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    adjusted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DispenseItem(Base):
    __tablename__ = "dispense_items"

    id = Column(Integer, primary_key=True, index=True)
    dispense_id = Column(Integer, ForeignKey("pharmacy_dispense.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drug_master.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("drug_stock.id"), nullable=True)
    drug_name = Column(String(200), nullable=False)
    batch_number = Column(String(100))
    expiry_date = Column(Date)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    tax_percent = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)
    dosage_instructions = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dispense = relationship("PharmacyDispense", back_populates="items")
