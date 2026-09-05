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


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)

    is_cash = Column(Boolean, default=False)
    is_bank = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    opening_balance = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(20), unique=True, index=True, nullable=False)

    entry_date = Column(DateTime(timezone=True), server_default=func.now())
    narration = Column(Text, nullable=False)
    reference = Column(String(200), nullable=True)

    cost_center = Column(String(100), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("JournalLine", back_populates="entry")


class GLPostingSourceType(str, enum.Enum):
    BILL = "bill"
    PAYMENT = "payment"
    PURCHASE_ORDER = "purchase_order"


class GLPosting(Base):
    """
    Tracks which external documents (Bills, Payments, Purchase Orders)
    have already been posted to the GL, and which journal entry resulted.
    This is what connects Accounts Receivable (via Bills) and Accounts
    Payable (via POs) into the double-entry ledger, without needing to
    modify the Billing/Inventory modules themselves - each source
    document can be posted at most once, enforced here.
    """
    __tablename__ = "gl_postings"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(GLPostingSourceType), nullable=False)
    source_id = Column(Integer, nullable=False)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    posted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    posted_at = Column(DateTime(timezone=True), server_default=func.now())


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    description = Column(Text, nullable=True)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="lines")
