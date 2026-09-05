from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.accounts import Account, JournalEntry, JournalLine, AccountType, GLPosting, GLPostingSourceType
from app.models.billing import Bill, Payment
from app.models.inventory import InventoryPurchaseOrder
from app.models.user import User
from app.schemas.accounts import (
    AccountCreate,
    AccountResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    QuickExpenseCreate,
    QuickIncomeCreate,
    AccountLedgerResponse,
    LedgerLineResponse,
    TrialBalanceResponse,
    TrialBalanceRow,
    ProfitLossResponse,
    BalanceSheetResponse,
    PostBillRequest,
    PostPaymentRequest,
    PostPORequest,
    BillSummaryResponse,
    POSummaryResponse,
    ARAPSummaryResponse,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])

DEBIT_NORMAL_TYPES = (AccountType.ASSET, AccountType.EXPENSE)
CREDIT_NORMAL_TYPES = (AccountType.LIABILITY, AccountType.EQUITY, AccountType.INCOME)


def _natural_balance(account_type: AccountType, opening_balance: float, debit_total: float, credit_total: float) -> float:
    if account_type in DEBIT_NORMAL_TYPES:
        return opening_balance + debit_total - credit_total
    return opening_balance + credit_total - debit_total


# ── CHART OF ACCOUNTS ─────────────────────────────────────────────

@router.post("/chart", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Account).filter(Account.account_code == data.account_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this code already exists")
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/chart", response_model=list[AccountResponse])
async def list_accounts(
    account_type: Optional[AccountType] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Account)
    if account_type:
        q = q.filter(Account.account_type == account_type)
    if active_only:
        q = q.filter(Account.is_active == True)  # noqa: E712
    return q.order_by(Account.account_code).all()


# ── JOURNAL ─────────────────────────────────────────────

def _post_journal_entry(db: Session, narration: str, reference: Optional[str], cost_center: Optional[str],
                         entry_date: Optional[datetime], lines_data: list, created_by: int) -> JournalEntry:
    if len(lines_data) < 2:
        raise HTTPException(status_code=400, detail="A journal entry needs at least 2 lines")

    total_debit = sum(line.debit for line in lines_data)
    total_credit = sum(line.credit for line in lines_data)
    if round(total_debit, 2) != round(total_credit, 2):
        raise HTTPException(
            status_code=400,
            detail=f"Journal entry is not balanced: total debits {total_debit} != total credits {total_credit}",
        )
    if total_debit == 0:
        raise HTTPException(status_code=400, detail="Journal entry cannot have zero total value")

    for line in lines_data:
        if line.debit and line.credit:
            raise HTTPException(status_code=400, detail="A single line cannot have both debit and credit")
        if not line.debit and not line.credit:
            raise HTTPException(status_code=400, detail="Each line must have either a debit or a credit amount")
        account = db.query(Account).filter(Account.id == line.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {line.account_id} not found")

    entry_data = {
        "narration": narration,
        "reference": reference,
        "cost_center": cost_center,
        "created_by": created_by,
    }
    if entry_date:
        entry_data["entry_date"] = entry_date

    attempt_base = next_sequence_number(db, JournalEntry)
    entry = None
    last_error = None
    for i in range(MAX_RETRIES):
        entry_data["entry_number"] = f"JE{attempt_base + i:07d}"
        entry = JournalEntry(**entry_data)
        db.add(entry)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            entry = None
    if last_error:
        raise last_error

    for line in lines_data:
        db.add(JournalLine(
            entry_id=entry.id,
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
        ))

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/journal", response_model=JournalEntryResponse, status_code=201)
async def create_journal_entry(
    data: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _post_journal_entry(
        db, data.narration, data.reference, data.cost_center, data.entry_date, data.lines, current_user.id
    )


@router.post("/journal/quick-expense", response_model=JournalEntryResponse, status_code=201)
async def quick_expense(
    data: QuickExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.accounts import JournalLineInput

    lines = [
        JournalLineInput(account_id=data.expense_account_id, debit=data.amount, description=data.narration),
        JournalLineInput(account_id=data.payment_account_id, credit=data.amount, description=data.narration),
    ]
    return _post_journal_entry(db, data.narration, data.reference, data.cost_center, None, lines, current_user.id)


@router.post("/journal/quick-income", response_model=JournalEntryResponse, status_code=201)
async def quick_income(
    data: QuickIncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.accounts import JournalLineInput

    lines = [
        JournalLineInput(account_id=data.receipt_account_id, debit=data.amount, description=data.narration),
        JournalLineInput(account_id=data.income_account_id, credit=data.amount, description=data.narration),
    ]
    return _post_journal_entry(db, data.narration, data.reference, data.cost_center, None, lines, current_user.id)


@router.get("/journal", response_model=list[JournalEntryResponse])
async def list_journal_entries(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(JournalEntry).order_by(JournalEntry.entry_date.desc()).limit(limit).all()


# ── LEDGER ─────────────────────────────────────────────

@router.get("/ledger/{account_id}", response_model=AccountLedgerResponse)
async def account_ledger(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    lines = (
        db.query(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .filter(JournalLine.account_id == account_id)
        .order_by(JournalEntry.entry_date.asc(), JournalEntry.id.asc())
        .all()
    )

    is_debit_normal = account.account_type in DEBIT_NORMAL_TYPES
    running = account.opening_balance
    ledger_lines = []
    for line in lines:
        if is_debit_normal:
            running += line.debit - line.credit
        else:
            running += line.credit - line.debit
        ledger_lines.append(LedgerLineResponse(
            entry_id=line.entry.id,
            entry_number=line.entry.entry_number,
            entry_date=line.entry.entry_date,
            narration=line.entry.narration,
            debit=line.debit,
            credit=line.credit,
            running_balance=round(running, 2),
        ))

    return AccountLedgerResponse(
        account=account,
        opening_balance=account.opening_balance,
        lines=ledger_lines,
        closing_balance=round(running, 2),
    )


@router.get("/cash-book", response_model=list[AccountLedgerResponse])
async def cash_book(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cash_accounts = db.query(Account).filter(Account.is_cash == True).all()  # noqa: E712
    return [await account_ledger(a.id, db, current_user) for a in cash_accounts]


@router.get("/bank-book", response_model=list[AccountLedgerResponse])
async def bank_book(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bank_accounts = db.query(Account).filter(Account.is_bank == True).all()  # noqa: E712
    return [await account_ledger(a.id, db, current_user) for a in bank_accounts]


# ── REPORTS ─────────────────────────────────────────────

def _trial_balance_rows(db: Session, up_to_date: Optional[datetime] = None) -> list:
    accounts = db.query(Account).filter(Account.is_active == True).order_by(Account.account_code).all()  # noqa: E712
    rows = []
    for account in accounts:
        q = db.query(JournalLine).filter(JournalLine.account_id == account.id)
        if up_to_date:
            q = q.join(JournalEntry, JournalLine.entry_id == JournalEntry.id).filter(JournalEntry.entry_date <= up_to_date)
        lines = q.all()
        debit_total = sum(l.debit for l in lines)
        credit_total = sum(l.credit for l in lines)
        balance = _natural_balance(account.account_type, account.opening_balance, debit_total, credit_total)
        rows.append(TrialBalanceRow(
            account_id=account.id,
            account_code=account.account_code,
            account_name=account.name,
            account_type=account.account_type,
            debit_total=round(debit_total, 2),
            credit_total=round(credit_total, 2),
            balance=round(balance, 2),
        ))
    return rows


@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
async def trial_balance(
    as_of_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _trial_balance_rows(db, as_of_date)
    total_debits = round(sum(r.debit_total for r in rows), 2)
    total_credits = round(sum(r.credit_total for r in rows), 2)
    return TrialBalanceResponse(
        rows=rows,
        total_debits=total_debits,
        total_credits=total_credits,
        is_balanced=abs(total_debits - total_credits) < 0.01,
    )


@router.get("/reports/profit-loss", response_model=ProfitLossResponse)
async def profit_loss(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accounts = db.query(Account).filter(
        Account.account_type.in_([AccountType.INCOME, AccountType.EXPENSE]),
        Account.is_active == True,  # noqa: E712
    ).all()

    income_breakdown, expense_breakdown = [], []
    for account in accounts:
        q = db.query(JournalLine).join(JournalEntry, JournalLine.entry_id == JournalEntry.id).filter(JournalLine.account_id == account.id)
        if period_start:
            q = q.filter(JournalEntry.entry_date >= period_start)
        if period_end:
            q = q.filter(JournalEntry.entry_date <= period_end)
        lines = q.all()
        debit_total = sum(l.debit for l in lines)
        credit_total = sum(l.credit for l in lines)
        balance = _natural_balance(account.account_type, 0.0, debit_total, credit_total)
        row = TrialBalanceRow(
            account_id=account.id, account_code=account.account_code, account_name=account.name,
            account_type=account.account_type, debit_total=round(debit_total, 2),
            credit_total=round(credit_total, 2), balance=round(balance, 2),
        )
        if account.account_type == AccountType.INCOME:
            income_breakdown.append(row)
        else:
            expense_breakdown.append(row)

    income_total = round(sum(r.balance for r in income_breakdown), 2)
    expense_total = round(sum(r.balance for r in expense_breakdown), 2)

    return ProfitLossResponse(
        period_start=period_start,
        period_end=period_end,
        income_total=income_total,
        expense_total=expense_total,
        net_profit=round(income_total - expense_total, 2),
        income_breakdown=income_breakdown,
        expense_breakdown=expense_breakdown,
    )


@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse)
async def balance_sheet(
    as_of_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _trial_balance_rows(db, as_of_date)
    assets = [r for r in rows if r.account_type == AccountType.ASSET]
    liabilities = [r for r in rows if r.account_type == AccountType.LIABILITY]
    equity = [r for r in rows if r.account_type == AccountType.EQUITY]

    asset_total = round(sum(r.balance for r in assets), 2)
    liability_total = round(sum(r.balance for r in liabilities), 2)
    equity_total = round(sum(r.balance for r in equity), 2)

    pl = await profit_loss(None, as_of_date, db, current_user)
    retained_earnings = pl.net_profit

    is_balanced = abs(asset_total - (liability_total + equity_total + retained_earnings)) < 0.01

    return BalanceSheetResponse(
        as_of_date=as_of_date,
        asset_total=asset_total,
        liability_total=liability_total,
        equity_total=equity_total,
        retained_earnings=retained_earnings,
        is_balanced=is_balanced,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
    )


@router.get("/ar/bills", response_model=list[BillSummaryResponse])
async def list_postable_bills(
    unposted_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bills = db.query(Bill).order_by(Bill.bill_date.desc()).limit(200).all()
    posted_ids = {p.source_id for p in db.query(GLPosting).filter(GLPosting.source_type == GLPostingSourceType.BILL).all()}
    results = [
        BillSummaryResponse(
            bill_id=b.id, bill_number=b.bill_number, patient_id=b.patient_id,
            gross_total=b.gross_total, paid_amount=b.paid_amount, balance_amount=b.balance_amount,
            already_posted=b.id in posted_ids,
        )
        for b in bills
    ]
    if unposted_only:
        results = [r for r in results if not r.already_posted]
    return results


@router.post("/ar/bills/{bill_id}/post", response_model=JournalEntryResponse, status_code=201)
async def post_bill_to_gl(
    bill_id: int,
    data: PostBillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit Accounts Receivable, Credit Revenue for the bill's gross total."""
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    already = db.query(GLPosting).filter(GLPosting.source_type == GLPostingSourceType.BILL, GLPosting.source_id == bill_id).first()
    if already:
        raise HTTPException(status_code=400, detail="This bill has already been posted to the ledger")
    if bill.gross_total <= 0:
        raise HTTPException(status_code=400, detail="Bill has no value to post")

    from app.schemas.accounts import JournalLineInput
    lines = [
        JournalLineInput(account_id=data.receivable_account_id, debit=bill.gross_total, description=f"AR for bill {bill.bill_number}"),
        JournalLineInput(account_id=data.revenue_account_id, credit=bill.gross_total, description=f"Revenue for bill {bill.bill_number}"),
    ]
    entry = _post_journal_entry(db, f"Bill {bill.bill_number} - patient revenue", bill.bill_number, None, None, lines, current_user.id)
    db.add(GLPosting(source_type=GLPostingSourceType.BILL, source_id=bill_id, journal_entry_id=entry.id, posted_by=current_user.id))
    db.commit()
    return entry


@router.post("/ar/payments/{payment_id}/post", response_model=JournalEntryResponse, status_code=201)
async def post_payment_to_gl(
    payment_id: int,
    data: PostPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit Cash/Bank, Credit Accounts Receivable when a patient pays a bill."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    already = db.query(GLPosting).filter(GLPosting.source_type == GLPostingSourceType.PAYMENT, GLPosting.source_id == payment_id).first()
    if already:
        raise HTTPException(status_code=400, detail="This payment has already been posted to the ledger")
    if payment.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment has no value to post")

    from app.schemas.accounts import JournalLineInput
    lines = [
        JournalLineInput(account_id=data.cash_bank_account_id, debit=payment.amount, description=f"Receipt for payment {payment.payment_number}"),
        JournalLineInput(account_id=data.receivable_account_id, credit=payment.amount, description=f"AR settled by payment {payment.payment_number}"),
    ]
    entry = _post_journal_entry(db, f"Payment {payment.payment_number} received", payment.payment_number, None, None, lines, current_user.id)
    db.add(GLPosting(source_type=GLPostingSourceType.PAYMENT, source_id=payment_id, journal_entry_id=entry.id, posted_by=current_user.id))
    db.commit()
    return entry


@router.get("/ap/purchase-orders", response_model=list[POSummaryResponse])
async def list_postable_pos(
    unposted_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pos = db.query(InventoryPurchaseOrder).order_by(InventoryPurchaseOrder.order_date.desc()).limit(200).all()
    posted_ids = {p.source_id for p in db.query(GLPosting).filter(GLPosting.source_type == GLPostingSourceType.PURCHASE_ORDER).all()}
    results = []
    for po in pos:
        total_value = sum(item.quantity_ordered * item.unit_price for item in po.items)
        results.append(POSummaryResponse(
            po_id=po.id, po_number=po.po_number, vendor_id=po.vendor_id,
            total_value=round(total_value, 2), already_posted=po.id in posted_ids,
        ))
    if unposted_only:
        results = [r for r in results if not r.already_posted]
    return results


@router.post("/ap/purchase-orders/{po_id}/post", response_model=JournalEntryResponse, status_code=201)
async def post_po_to_gl(
    po_id: int,
    data: PostPORequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit Expense/Asset, Credit Accounts Payable for the PO's total value."""
    po = db.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    already = db.query(GLPosting).filter(GLPosting.source_type == GLPostingSourceType.PURCHASE_ORDER, GLPosting.source_id == po_id).first()
    if already:
        raise HTTPException(status_code=400, detail="This purchase order has already been posted to the ledger")

    total_value = sum(item.quantity_ordered * item.unit_price for item in po.items)
    if total_value <= 0:
        raise HTTPException(status_code=400, detail="Purchase order has no value to post")

    from app.schemas.accounts import JournalLineInput
    lines = [
        JournalLineInput(account_id=data.expense_or_asset_account_id, debit=round(total_value, 2), description=f"Goods/services from PO {po.po_number}"),
        JournalLineInput(account_id=data.payable_account_id, credit=round(total_value, 2), description=f"AP for PO {po.po_number}"),
    ]
    entry = _post_journal_entry(db, f"PO {po.po_number} - vendor liability", po.po_number, None, None, lines, current_user.id)
    db.add(GLPosting(source_type=GLPostingSourceType.PURCHASE_ORDER, source_id=po_id, journal_entry_id=entry.id, posted_by=current_user.id))
    db.commit()
    return entry


@router.get("/ar/summary", response_model=list[ARAPSummaryResponse])
async def ar_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Outstanding balance on whichever accounts have actually been used
    as the receivable account in bill postings."""
    rows = _trial_balance_rows(db)
    entry_account_ids = set()
    for jl in db.query(JournalLine).join(JournalEntry, JournalLine.entry_id == JournalEntry.id).join(GLPosting, GLPosting.journal_entry_id == JournalEntry.id).filter(GLPosting.source_type == GLPostingSourceType.BILL).all():
        entry_account_ids.add(jl.account_id)
    return [ARAPSummaryResponse(account_id=r.account_id, account_code=r.account_code, account_name=r.account_name, balance=r.balance) for r in rows if r.account_id in entry_account_ids]


@router.get("/ap/summary", response_model=list[ARAPSummaryResponse])
async def ap_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _trial_balance_rows(db)
    entry_account_ids = set()
    for jl in db.query(JournalLine).join(JournalEntry, JournalLine.entry_id == JournalEntry.id).join(GLPosting, GLPosting.journal_entry_id == JournalEntry.id).filter(GLPosting.source_type == GLPostingSourceType.PURCHASE_ORDER).all():
        entry_account_ids.add(jl.account_id)
    return [ARAPSummaryResponse(account_id=r.account_id, account_code=r.account_code, account_name=r.account_name, balance=r.balance) for r in rows if r.account_id in entry_account_ids]


@router.get("/dashboard/stats")
async def accounts_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_accounts = db.query(Account).filter(Account.is_active == True).count()  # noqa: E712
    total_entries = db.query(JournalEntry).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    entries_today = db.query(JournalEntry).filter(JournalEntry.entry_date >= today_start).count()

    pl = await profit_loss(None, None, db, current_user)

    return {
        "total_accounts": total_accounts,
        "total_journal_entries": total_entries,
        "entries_today": entries_today,
        "net_profit_all_time": pl.net_profit,
    }
