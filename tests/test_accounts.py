"""
Accounts module test: this is real double-entry bookkeeping, so the tests
focus heavily on accounting correctness - balanced entries enforced,
ledger running balances correct, trial balance always balances, P&L and
balance sheet numbers actually reconcile.
"""

state = {}


def test_create_chart_of_accounts(client, auth_headers):
    accounts = [
        ("1000", "Cash in Hand", "asset", True, False, 10000.0),
        ("1100", "Bank Account", "asset", False, True, 50000.0),
        ("2000", "Accounts Payable", "liability", False, False, 0.0),
        ("3000", "Owner's Equity", "equity", False, False, 60000.0),
        ("4000", "Patient Service Revenue", "income", False, False, 0.0),
        ("5000", "Staff Salaries", "expense", False, False, 0.0),
        ("5100", "Office Supplies Expense", "expense", False, False, 0.0),
    ]
    state["accounts"] = {}
    for code, name, atype, is_cash, is_bank, opening in accounts:
        resp = client.post("/api/accounts/chart", json={
            "account_code": code, "name": name, "account_type": atype,
            "is_cash": is_cash, "is_bank": is_bank, "opening_balance": opening,
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        state["accounts"][code] = resp.json()["id"]


def test_duplicate_account_code_rejected(client, auth_headers):
    resp = client.post("/api/accounts/chart", json={
        "account_code": "1000", "name": "Duplicate Cash", "account_type": "asset",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_unbalanced_entry_rejected(client, auth_headers):
    resp = client.post("/api/accounts/journal", json={
        "narration": "Unbalanced test entry",
        "lines": [
            {"account_id": state["accounts"]["5000"], "debit": 1000.0},
            {"account_id": state["accounts"]["1000"], "credit": 500.0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_single_line_entry_rejected(client, auth_headers):
    resp = client.post("/api/accounts/journal", json={
        "narration": "Single line",
        "lines": [{"account_id": state["accounts"]["5000"], "debit": 100.0}],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_line_with_both_debit_and_credit_rejected(client, auth_headers):
    resp = client.post("/api/accounts/journal", json={
        "narration": "Bad line",
        "lines": [
            {"account_id": state["accounts"]["5000"], "debit": 100.0, "credit": 100.0},
            {"account_id": state["accounts"]["1000"], "credit": 100.0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_balanced_journal_entry_posts(client, auth_headers):
    resp = client.post("/api/accounts/journal", json={
        "narration": "Salary payment for August",
        "reference": "SAL-AUG",
        "lines": [
            {"account_id": state["accounts"]["5000"], "debit": 5000.0},
            {"account_id": state["accounts"]["1100"], "credit": 5000.0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["entry_number"].startswith("JE")
    assert len(body["lines"]) == 2


def test_quick_expense(client, auth_headers):
    resp = client.post("/api/accounts/journal/quick-expense", json={
        "expense_account_id": state["accounts"]["5100"],
        "payment_account_id": state["accounts"]["1000"],
        "amount": 500.0,
        "narration": "Bought printer paper and pens",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["lines"]) == 2
    debit_line = next(l for l in body["lines"] if l["debit"] > 0)
    credit_line = next(l for l in body["lines"] if l["credit"] > 0)
    assert debit_line["account_id"] == state["accounts"]["5100"]
    assert credit_line["account_id"] == state["accounts"]["1000"]


def test_quick_income(client, auth_headers):
    resp = client.post("/api/accounts/journal/quick-income", json={
        "income_account_id": state["accounts"]["4000"],
        "receipt_account_id": state["accounts"]["1100"],
        "amount": 15000.0,
        "narration": "OPD consultation revenue for the day",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text


def test_cash_ledger_running_balance(client, auth_headers):
    """
    Cash account (1000): opening 10000, -500 (office supplies expense
    paid from cash) => closing balance should be 9500.
    """
    resp = client.get(f"/api/accounts/ledger/{state['accounts']['1000']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["opening_balance"] == 10000.0
    assert body["closing_balance"] == 9500.0
    assert len(body["lines"]) == 1
    assert body["lines"][0]["running_balance"] == 9500.0


def test_bank_ledger_running_balance(client, auth_headers):
    """
    Bank account (1100): opening 50000, -5000 (salary), +15000 (income)
    => closing balance should be 60000.
    """
    resp = client.get(f"/api/accounts/ledger/{state['accounts']['1100']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["opening_balance"] == 50000.0
    assert body["closing_balance"] == 60000.0


def test_cash_book_lists_cash_flagged_accounts(client, auth_headers):
    resp = client.get("/api/accounts/cash-book", headers=auth_headers)
    assert resp.status_code == 200
    account_ids = [entry["account"]["id"] for entry in resp.json()]
    assert state["accounts"]["1000"] in account_ids
    assert state["accounts"]["1100"] not in account_ids


def test_bank_book_lists_bank_flagged_accounts(client, auth_headers):
    resp = client.get("/api/accounts/bank-book", headers=auth_headers)
    assert resp.status_code == 200
    account_ids = [entry["account"]["id"] for entry in resp.json()]
    assert state["accounts"]["1100"] in account_ids
    assert state["accounts"]["1000"] not in account_ids


def test_trial_balance_is_balanced(client, auth_headers):
    """
    The single most important correctness check: total debits across
    every journal line must always equal total credits, by construction
    (since every entry we posted was itself balanced).
    """
    resp = client.get("/api/accounts/reports/trial-balance", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_balanced"] is True
    assert body["total_debits"] == body["total_credits"]


def test_profit_and_loss(client, auth_headers):
    """
    Income posted: 15000. Expenses posted: 5000 (salary) + 500 (supplies)
    = 5500. Net profit should be 15000 - 5500 = 9500.
    """
    resp = client.get("/api/accounts/reports/profit-loss", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["income_total"] == 15000.0
    assert body["expense_total"] == 5500.0
    assert body["net_profit"] == 9500.0


def test_balance_sheet_balances(client, auth_headers):
    """
    Assets = Liabilities + Equity + Retained Earnings must hold.
    Cash: 9500, Bank: 60000 => Assets = 69500
    Liabilities = 0, Equity (opening) = 60000, Retained earnings = 9500
    69500 == 0 + 60000 + 9500 -> balanced.
    """
    resp = client.get("/api/accounts/reports/balance-sheet", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["asset_total"] == 69500.0
    assert body["retained_earnings"] == 9500.0
    assert body["is_balanced"] is True


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/accounts/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_accounts"] >= 7
    assert body["total_journal_entries"] >= 3
    assert body["net_profit_all_time"] == 9500.0
