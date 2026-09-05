"""
Tests for the Group 3 balance items: AR/AP GL integration (Bills and
Purchase Orders posting into the double-entry ledger) and Medical
Coding + RCM worklist.
"""

state = {}


def test_setup_gl_accounts(client, auth_headers):
    accs = [
        ("9000", "Accounts Receivable", "asset", False, False),
        ("9100", "Accounts Payable", "liability", False, False),
        ("9200", "Patient Revenue", "income", False, False),
        ("9300", "Supplies Expense", "expense", False, False),
        ("9400", "Operating Cash", "asset", True, False),
    ]
    state["accs"] = {}
    for code, name, atype, is_cash, is_bank in accs:
        resp = client.post("/api/accounts/chart", json={
            "account_code": code, "name": name, "account_type": atype,
            "is_cash": is_cash, "is_bank": is_bank,
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        state["accs"][code] = resp.json()["id"]


def test_setup_patient_and_bill(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "ARTest", "last_name": "Patient", "date_of_birth": "1985-05-05",
        "gender": "male", "phone": "9123409001",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["patient_id"] = resp.json()["id"]

    resp = client.post("/api/billing/bills", json={
        "patient_id": state["patient_id"],
        "bill_type": "opd",
        "items": [
            {"item_name": "Consultation", "category": "consultation", "quantity": 1, "unit_price": 1000.0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["bill_id"] = resp.json()["id"]


def test_post_bill_to_gl(client, auth_headers):
    resp = client.post(f"/api/accounts/ar/bills/{state['bill_id']}/post", json={
        "receivable_account_id": state["accs"]["9000"],
        "revenue_account_id": state["accs"]["9200"],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["lines"]) == 2


def test_cannot_post_same_bill_twice(client, auth_headers):
    resp = client.post(f"/api/accounts/ar/bills/{state['bill_id']}/post", json={
        "receivable_account_id": state["accs"]["9000"],
        "revenue_account_id": state["accs"]["9200"],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_bill_shows_as_posted(client, auth_headers):
    resp = client.get("/api/accounts/ar/bills?unposted_only=true", headers=auth_headers)
    assert resp.status_code == 200
    ids = [b["bill_id"] for b in resp.json()]
    assert state["bill_id"] not in ids


def test_ar_receivable_account_balance_reflects_bill(client, auth_headers):
    resp = client.get(f"/api/accounts/ledger/{state['accs']['9000']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["closing_balance"] == 1000.0


def test_post_payment_to_gl(client, auth_headers):
    resp = client.post("/api/billing/payments", json={
        "bill_id": state["bill_id"],
        "patient_id": state["patient_id"],
        "amount": 1000.0,
        "payment_mode": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["payment_id"] = resp.json()["id"]

    resp = client.post(f"/api/accounts/ar/payments/{state['payment_id']}/post", json={
        "receivable_account_id": state["accs"]["9000"],
        "cash_bank_account_id": state["accs"]["9400"],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text


def test_receivable_cleared_after_payment_posted(client, auth_headers):
    resp = client.get(f"/api/accounts/ledger/{state['accs']['9000']}", headers=auth_headers)
    assert resp.json()["closing_balance"] == 0.0


def test_cannot_post_same_payment_twice(client, auth_headers):
    resp = client.post(f"/api/accounts/ar/payments/{state['payment_id']}/post", json={
        "receivable_account_id": state["accs"]["9000"],
        "cash_bank_account_id": state["accs"]["9400"],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_setup_vendor_and_po(client, auth_headers):
    resp = client.post("/api/inventory/vendors", json={"name": "AP Test Vendor"}, headers=auth_headers)
    vendor_id = resp.json()["id"]

    resp = client.post("/api/inventory/items", json={"item_code": "AP-TEST-ITEM", "name": "AP Test Item"}, headers=auth_headers)
    item_id = resp.json()["id"]

    resp = client.post("/api/inventory/purchase-orders", json={
        "vendor_id": vendor_id,
        "items": [{"item_id": item_id, "quantity_ordered": 10, "unit_price": 200.0}],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["po_id"] = resp.json()["id"]


def test_post_po_to_gl(client, auth_headers):
    resp = client.post(f"/api/accounts/ap/purchase-orders/{state['po_id']}/post", json={
        "payable_account_id": state["accs"]["9100"],
        "expense_or_asset_account_id": state["accs"]["9300"],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/accounts/ledger/{state['accs']['9100']}", headers=auth_headers)
    assert resp.json()["closing_balance"] == 2000.0


def test_cannot_post_same_po_twice(client, auth_headers):
    resp = client.post(f"/api/accounts/ap/purchase-orders/{state['po_id']}/post", json={
        "payable_account_id": state["accs"]["9100"],
        "expense_or_asset_account_id": state["accs"]["9300"],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_ap_summary_shows_payable_account(client, auth_headers):
    resp = client.get("/api/accounts/ap/summary", headers=auth_headers)
    assert resp.status_code == 200
    ids = [r["account_id"] for r in resp.json()]
    assert state["accs"]["9100"] in ids


# ── MEDICAL CODING & RCM ─────────────────────────────────────────────

def test_create_medical_codes(client, auth_headers):
    resp = client.post("/api/medical-coding/codes", json={
        "code_system": "icd10", "code": "J18.9", "description": "Pneumonia, unspecified",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["diag_code_id"] = resp.json()["id"]

    resp = client.post("/api/medical-coding/codes", json={
        "code_system": "cpt", "code": "99213", "description": "Office visit, established patient",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["proc_code_id"] = resp.json()["id"]


def test_duplicate_code_rejected(client, auth_headers):
    resp = client.post("/api/medical-coding/codes", json={
        "code_system": "icd10", "code": "J18.9", "description": "Duplicate",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_search_codes(client, auth_headers):
    resp = client.get("/api/medical-coding/codes?search=pneumonia", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_rcm_worklist_endpoint_works(client, auth_headers):
    resp = client.get("/api/medical-coding/rcm/worklist", headers=auth_headers)
    assert resp.status_code == 200


def test_patient_coding_and_dashboard(client, auth_headers):
    resp = client.post("/api/medical-coding/patient-coding", json={
        "bill_id": state["bill_id"],
        "patient_id": state["patient_id"],
        "code_id": state["diag_code_id"],
        "code_type": "diagnosis",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.post("/api/medical-coding/patient-coding", json={
        "bill_id": state["bill_id"],
        "patient_id": state["patient_id"],
        "code_id": state["proc_code_id"],
        "code_type": "procedure",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/medical-coding/patient-coding?bill_id={state['bill_id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/medical-coding/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_codes"] >= 2
