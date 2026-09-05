"""
Tests for Group 1 items #1 (Hospital/Org Setup), #3 (Department & Unit
Management - extending the existing Department table with branch
linkage), and #4 (Master Data Management - tax rate, payment mode).
"""

state = {}


def test_create_branch(client, auth_headers):
    resp = client.post("/api/organization/branches", json={
        "branch_code": "MAIN",
        "name": "Main Hospital",
        "city": "Coimbatore",
        "is_head_office": True,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["branch_id"] = resp.json()["id"]


def test_duplicate_branch_code_rejected(client, auth_headers):
    resp = client.post("/api/organization/branches", json={
        "branch_code": "MAIN", "name": "Duplicate Branch",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_list_branches(client, auth_headers):
    resp = client.get("/api/organization/branches", headers=auth_headers)
    assert resp.status_code == 200
    ids = [b["id"] for b in resp.json()]
    assert state["branch_id"] in ids


def test_update_branch(client, auth_headers):
    resp = client.put(f"/api/organization/branches/{state['branch_id']}", json={
        "city": "Chennai",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["city"] == "Chennai"


def test_department_can_link_to_branch(client, auth_headers):
    resp = client.post("/api/hr/departments", json={
        "branch_id": state["branch_id"],
        "dept_code": "CARD-ORG-TEST",
        "name": "Cardiology (Org Test)",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["branch_id"] == state["branch_id"]
    state["dept_id"] = body["id"]


def test_filter_departments_by_branch(client, auth_headers):
    resp = client.get(f"/api/hr/departments?branch_id={state['branch_id']}", headers=auth_headers)
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()]
    assert state["dept_id"] in ids


def test_create_tax_rate(client, auth_headers):
    resp = client.post("/api/organization/tax-rates", json={
        "name": "GST 18%", "percent": 18.0, "is_default": True,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["tax18_id"] = resp.json()["id"]
    assert resp.json()["is_default"] is True


def test_second_default_unsets_first(client, auth_headers):
    resp = client.post("/api/organization/tax-rates", json={
        "name": "GST 5%", "percent": 5.0, "is_default": True,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["tax5_id"] = resp.json()["id"]

    resp = client.get("/api/organization/tax-rates", headers=auth_headers)
    defaults = [r for r in resp.json() if r["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == state["tax5_id"]


def test_set_default_tax_rate_explicitly(client, auth_headers):
    resp = client.put(f"/api/organization/tax-rates/{state['tax18_id']}/set-default", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_default"] is True

    resp = client.get("/api/organization/tax-rates", headers=auth_headers)
    defaults = [r for r in resp.json() if r["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == state["tax18_id"]


def test_create_payment_mode(client, auth_headers):
    resp = client.post("/api/organization/payment-modes", json={
        "code": "upi", "display_name": "UPI",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["pm_id"] = resp.json()["id"]
    assert resp.json()["is_enabled"] is True


def test_duplicate_payment_mode_rejected(client, auth_headers):
    resp = client.post("/api/organization/payment-modes", json={
        "code": "upi", "display_name": "UPI Duplicate",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_toggle_payment_mode(client, auth_headers):
    resp = client.put(f"/api/organization/payment-modes/{state['pm_id']}/toggle", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_enabled"] is False

    resp = client.get("/api/organization/payment-modes?enabled_only=true", headers=auth_headers)
    ids = [p["id"] for p in resp.json()]
    assert state["pm_id"] not in ids
