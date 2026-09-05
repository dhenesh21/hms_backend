"""
Inventory module test: item + vendor setup -> PO -> partial GRN -> full GRN
-> stock verification -> issue/transfer/return/adjustment movements with
quantity validation.
"""

state = {}


def test_create_item(client, auth_headers):
    resp = client.post("/api/inventory/items", json={
        "item_code": "GLOVE-M",
        "name": "Examination Gloves (Medium)",
        "category": "consumable",
        "unit": "box",
        "reorder_level": 20,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["item_id"] = resp.json()["id"]


def test_duplicate_item_code_rejected(client, auth_headers):
    resp = client.post("/api/inventory/items", json={
        "item_code": "GLOVE-M",
        "name": "Duplicate",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_vendor(client, auth_headers):
    resp = client.post("/api/inventory/vendors", json={
        "name": "MedSupply Co",
        "contact_person": "Ravi",
        "phone": "9876543210",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["vendor_id"] = resp.json()["id"]


def test_create_purchase_order(client, auth_headers):
    resp = client.post("/api/inventory/purchase-orders", json={
        "vendor_id": state["vendor_id"],
        "items": [
            {"item_id": state["item_id"], "quantity_ordered": 100, "unit_price": 50.0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["po_number"].startswith("PO")
    assert body["status"] == "sent"
    assert len(body["items"]) == 1
    state["po_id"] = body["id"]
    state["po_item_id"] = body["items"][0]["id"]


def test_partial_grn(client, auth_headers):
    resp = client.post("/api/inventory/grn", json={
        "po_id": state["po_id"],
        "items": [
            {"po_item_id": state["po_item_id"], "item_id": state["item_id"], "quantity_received": 60},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["grn1_id"] = resp.json()["id"]

    resp = client.get(f"/api/inventory/purchase-orders/{state['po_id']}", headers=auth_headers)
    assert resp.json()["status"] == "partially_received"


def test_stock_updated_after_partial_grn(client, auth_headers):
    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    assert resp.status_code == 200
    stock = resp.json()[0]
    assert stock["quantity_available"] == 60


def test_cannot_over_receive(client, auth_headers):
    resp = client.post("/api/inventory/grn", json={
        "po_id": state["po_id"],
        "items": [
            {"po_item_id": state["po_item_id"], "item_id": state["item_id"], "quantity_received": 100},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_complete_grn(client, auth_headers):
    resp = client.post("/api/inventory/grn", json={
        "po_id": state["po_id"],
        "items": [
            {"po_item_id": state["po_item_id"], "item_id": state["item_id"], "quantity_received": 40},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/inventory/purchase-orders/{state['po_id']}", headers=auth_headers)
    assert resp.json()["status"] == "received"


def test_stock_fully_updated(client, auth_headers):
    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    stock = resp.json()[0]
    assert stock["quantity_available"] == 100


def test_cannot_receive_against_completed_po(client, auth_headers):
    resp = client.post("/api/inventory/grn", json={
        "po_id": state["po_id"],
        "items": [
            {"po_item_id": state["po_item_id"], "item_id": state["item_id"], "quantity_received": 1},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_issue_stock(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "issue",
        "quantity": 30,
        "department": "OPD",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    assert resp.json()[0]["quantity_available"] == 70


def test_cannot_issue_more_than_available(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "issue",
        "quantity": 1000,
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_transfer_stock_between_locations(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "transfer",
        "quantity": 20,
        "from_location": "Central Store",
        "to_location": "ICU Store",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    stocks = {s["location"]: s["quantity_available"] for s in resp.json()}
    assert stocks["Central Store"] == 50
    assert stocks["ICU Store"] == 20


def test_return_stock(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "return",
        "quantity": 5,
        "to_location": "Central Store",
        "reason": "Unused, returning to central store",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    stocks = {s["location"]: s["quantity_available"] for s in resp.json()}
    assert stocks["Central Store"] == 55


def test_negative_adjustment(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "adjustment",
        "quantity": -3,
        "to_location": "Central Store",
        "reason": "Stock count correction - 3 damaged",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/inventory/stock?item_id={state['item_id']}", headers=auth_headers)
    stocks = {s["location"]: s["quantity_available"] for s in resp.json()}
    assert stocks["Central Store"] == 52


def test_adjustment_cannot_go_negative(client, auth_headers):
    resp = client.post("/api/inventory/movements", json={
        "item_id": state["item_id"],
        "movement_type": "adjustment",
        "quantity": -9999,
        "to_location": "Central Store",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_low_stock_filter(client, auth_headers):
    resp = client.post("/api/inventory/items", json={
        "item_code": "SYRINGE-5ML",
        "name": "5ml Syringe",
        "reorder_level": 50,
    }, headers=auth_headers)
    low_item_id = resp.json()["id"]

    resp = client.post("/api/inventory/movements", json={
        "item_id": low_item_id,
        "movement_type": "adjustment",
        "quantity": 10,
        "to_location": "Central Store",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get("/api/inventory/stock?low_stock_only=true", headers=auth_headers)
    assert resp.status_code == 200
    item_ids = [s["item_id"] for s in resp.json()]
    assert low_item_id in item_ids


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/inventory/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_items"] >= 2
    assert body["movements_today"] >= 5
