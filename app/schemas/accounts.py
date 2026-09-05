from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.accounts import AccountType


class AccountCreate(BaseModel):
    account_code: str
    name: str
    account_type: AccountType
    is_cash: bool = False
    is_bank: bool = False
    opening_balance: float = 0.0
    notes: Optional[str] = None


class AccountResponse(BaseModel):
    id: int
    account_code: str
    name: str
    account_type: AccountType
    is_cash: bool
    is_bank: bool
    is_active: bool
    opening_balance: float
    notes: Optional[str]

    class Config:
        from_attributes = True


class JournalLineInput(BaseModel):
    account_id: int
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None


class JournalEntryCreate(BaseModel):
    narration: str
    reference: Optional[str] = None
    cost_center: Optional[str] = None
    entry_date: Optional[datetime] = None
    lines: list[JournalLineInput]


class JournalLineResponse(BaseModel):
    id: int
    account_id: int
    debit: float
    credit: float
    description: Optional[str]

    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    id: int
    entry_number: str
    entry_date: datetime
    narration: str
    reference: Optional[str]
    cost_center: Optional[str]
    lines: list[JournalLineResponse] = []

    class Config:
        from_attributes = True


class QuickExpenseCreate(BaseModel):
    expense_account_id: int
    payment_account_id: int
    amount: float
    narration: str
    reference: Optional[str] = None
    cost_center: Optional[str] = None


class QuickIncomeCreate(BaseModel):
    income_account_id: int
    receipt_account_id: int
    amount: float
    narration: str
    reference: Optional[str] = None
    cost_center: Optional[str] = None


class LedgerLineResponse(BaseModel):
    entry_id: int
    entry_number: str
    entry_date: datetime
    narration: str
    debit: float
    credit: float
    running_balance: float


class AccountLedgerResponse(BaseModel):
    account: AccountResponse
    opening_balance: float
    lines: list[LedgerLineResponse]
    closing_balance: float


class TrialBalanceRow(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: AccountType
    debit_total: float
    credit_total: float
    balance: float


class TrialBalanceResponse(BaseModel):
    rows: list[TrialBalanceRow]
    total_debits: float
    total_credits: float
    is_balanced: bool


class ProfitLossResponse(BaseModel):
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    income_total: float
    expense_total: float
    net_profit: float
    income_breakdown: list[TrialBalanceRow]
    expense_breakdown: list[TrialBalanceRow]


class BillSummaryResponse(BaseModel):
    bill_id: int
    bill_number: str
    patient_id: int
    gross_total: float
    paid_amount: float
    balance_amount: float
    already_posted: bool


class PostBillRequest(BaseModel):
    receivable_account_id: int
    revenue_account_id: int


class PostPaymentRequest(BaseModel):
    receivable_account_id: int
    cash_bank_account_id: int


class POSummaryResponse(BaseModel):
    po_id: int
    po_number: str
    vendor_id: int
    total_value: float
    already_posted: bool


class PostPORequest(BaseModel):
    payable_account_id: int
    expense_or_asset_account_id: int


class ARAPSummaryResponse(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    balance: float


class BalanceSheetResponse(BaseModel):
    as_of_date: Optional[datetime]
    asset_total: float
    liability_total: float
    equity_total: float
    retained_earnings: float
    is_balanced: bool
    assets: list[TrialBalanceRow]
    liabilities: list[TrialBalanceRow]
    equity: list[TrialBalanceRow]
