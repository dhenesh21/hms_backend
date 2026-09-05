from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class BillType(str, enum.Enum):
    OPD = "opd"
    IPD = "ipd"
    EMERGENCY = "emergency"
    DAY_CARE = "day_care"


class BillStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMode(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    NEFT = "neft"
    CHEQUE = "cheque"
    INSURANCE = "insurance"
    WALLET = "wallet"


class ServiceCategory(str, enum.Enum):
    CONSULTATION = "consultation"
    PROCEDURE = "procedure"
    LAB = "lab"
    RADIOLOGY = "radiology"
    PHARMACY = "pharmacy"
    ROOM_CHARGE = "room_charge"
    OT_CHARGE = "ot_charge"
    NURSING = "nursing"
    DIET = "diet"
    AMBULANCE = "ambulance"
    MISCELLANEOUS = "miscellaneous"


class ServiceMaster(Base):
    """Master price list for all services"""
    __tablename__ = "service_master"

    id = Column(Integer, primary_key=True, index=True)
    service_code = Column(String(20), unique=True, nullable=False, index=True)
    service_name = Column(String(300), nullable=False)
    category = Column(Enum(ServiceCategory), nullable=False)
    unit_price = Column(Float, nullable=False)
    tax_percent = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BillingPackage(Base):
    """Pre-defined billing packages (e.g. Normal Delivery Package)"""
    __tablename__ = "billing_packages"

    id = Column(Integer, primary_key=True, index=True)
    package_code = Column(String(20), unique=True, nullable=False)
    package_name = Column(String(300), nullable=False)
    description = Column(Text)
    total_price = Column(Float, nullable=False)
    validity_days = Column(Integer, default=30)
    inclusions = Column(JSON, default=list)   # kept for backward compatibility with any existing reads;
                                                # PackageLineItem below is the structured replacement.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PackageLineItem(Base):
    """
    Items 142-143 — the checklist flagged BillingPackage.inclusions as
    just a flat list of service codes with no per-item price/quantity/
    optionality, so a package's total_price had no traceable breakdown.
    This is that breakdown: one row per included service, each with its
    own quantity and the price actually attributed to it within the
    package (which is very often below that service's standalone
    ServiceMaster price - that's the whole point of a package discount,
    and now that discount is visible per-line instead of buried in one
    lump total_price on the package header).
    """
    __tablename__ = "package_line_items"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("billing_packages.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("service_master.id"), nullable=False)
    quantity = Column(Integer, default=1)
    package_price = Column(Float, nullable=False)     # price attributed to this line within the package
    standalone_price = Column(Float, nullable=True)    # snapshot of ServiceMaster.unit_price at package creation, for discount-visibility
    is_optional = Column(Boolean, default=False)       # e.g. "private room upgrade" offered but not mandatory
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String(20), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    bill_type = Column(Enum(BillType), nullable=False)
    status = Column(Enum(BillStatus), default=BillStatus.DRAFT)

    # References
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    package_id = Column(Integer, ForeignKey("billing_packages.id"), nullable=True)

    # Dates
    bill_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(Date)
    discharge_date = Column(DateTime(timezone=True))

    # Amounts
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_reason = Column(Text)
    discount_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    package_amount = Column(Float, default=0.0)
    gross_total = Column(Float, default=0.0)
    insurance_amount = Column(Float, default=0.0)
    patient_liability = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance_amount = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)

    # Insurance
    insurance_claim_id = Column(Integer, ForeignKey("insurance_claims.id"), nullable=True)

    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("service_master.id"), nullable=True)
    item_name = Column(String(300), nullable=False)
    category = Column(Enum(ServiceCategory), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    tax_percent = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)
    service_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bill = relationship("Bill", back_populates="items")


class RefundStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVERSED = "reversed"     # an approved refund that was itself later undone


class RefundRequest(Base):
    """
    Items 146-149 — `Payment.is_refund` and `Bill.refund_amount` already
    existed but nothing ever set them: there was no endpoint to request,
    approve, or reverse a refund. This is that workflow: a refund always
    starts as a request against a specific original Payment (never a bare
    number against a Bill - traceability to what's actually being refunded
    matters here), needs approval before any money/ledger effect happens,
    and can itself be reversed (e.g. a refund was approved in error, or the
    patient's card chargeback was disputed) - REVERSED puts the Bill's
    paid_amount/balance back to where they were before the refund, rather
    than just being a second refund pointed the other way.
    """
    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, index=True)
    refund_number = Column(String(20), unique=True, nullable=False)
    original_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(RefundStatus), default=RefundStatus.REQUESTED)

    refund_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)   # the negative Payment row created on approval

    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reversed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reversal_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String(20), unique=True, nullable=False, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())

    # Mode-specific details
    transaction_reference = Column(String(200))  # UPI ref, card last 4, cheque no
    bank_name = Column(String(100))
    cheque_date = Column(Date)

    # Insurance payment
    tpa_name = Column(String(200))
    insurance_approval_code = Column(String(100))

    notes = Column(Text)
    received_by = Column(Integer, ForeignKey("users.id"))
    is_advance = Column(Boolean, default=False)
    is_refund = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bill = relationship("Bill", back_populates="payments")


class AdvancePayment(Base):
    __tablename__ = "advance_payments"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(20), unique=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    transaction_reference = Column(String(200))
    balance_remaining = Column(Float)
    is_adjusted = Column(Boolean, default=False)
    adjusted_bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)
    received_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
