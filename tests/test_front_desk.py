"""
Front Desk module test: visitor check-in -> check-out, and lost & found
item report -> claim / mark-unclaimed.
"""

state = {}


def test_setup_patient(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "FrontDesk",
        "last_name": "TestPatient",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "phone": "9123408001",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["patient_id"] = resp.json()["id"]


def test_visitor_check_in(client, auth_headers):
    resp = client.post("/api/front-desk/visitors/check-in", json={
        "visitor_name": "Suresh Kumar",
        "visitor_phone": "9988776655",
        "relation_to_patient": "Brother",
        "patient_id": state["patient_id"],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["pass_number"].startswith("VIS")
    assert body["status"] == "checked_in"
    state["visitor_id"] = body["id"]


def test_visitor_appears_in_currently_in_list(client, auth_headers):
    resp = client.get("/api/front-desk/visitors/currently-in", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["visitor_id"] in ids


def test_visitor_check_out(client, auth_headers):
    resp = client.put(f"/api/front-desk/visitors/{state['visitor_id']}/check-out", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "checked_out"
    assert body["check_out_time"] is not None


def test_cannot_check_out_twice(client, auth_headers):
    resp = client.put(f"/api/front-desk/visitors/{state['visitor_id']}/check-out", headers=auth_headers)
    assert resp.status_code == 400


def test_visitor_no_longer_in_currently_in_list(client, auth_headers):
    resp = client.get("/api/front-desk/visitors/currently-in", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["visitor_id"] not in ids


def test_report_found_item(client, auth_headers):
    resp = client.post("/api/front-desk/lost-found", json={
        "entry_type": "found_item",
        "item_description": "Black wallet with ID cards",
        "location_found_lost": "OPD waiting area",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["item_number"].startswith("LF")
    assert body["status"] == "reported"
    state["item_id"] = body["id"]


def test_item_appears_in_pending_list(client, auth_headers):
    resp = client.get("/api/front-desk/lost-found?status=reported", headers=auth_headers)
    ids = [i["id"] for i in resp.json()]
    assert state["item_id"] in ids


def test_claim_item(client, auth_headers):
    resp = client.put(f"/api/front-desk/lost-found/{state['item_id']}/claim", json={
        "claimed_by": "Rajesh (owner)",
        "claim_verification": "Verified via ID card inside wallet matching claimant's name",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "claimed"
    assert body["claimed_date"] is not None


def test_cannot_claim_twice(client, auth_headers):
    resp = client.put(f"/api/front-desk/lost-found/{state['item_id']}/claim", json={
        "claimed_by": "Someone else",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_mark_unclaimed_item(client, auth_headers):
    resp = client.post("/api/front-desk/lost-found", json={
        "entry_type": "found_item",
        "item_description": "Old umbrella",
    }, headers=auth_headers)
    item_id = resp.json()["id"]

    resp = client.put(f"/api/front-desk/lost-found/{item_id}/mark-unclaimed", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "unclaimed"


def test_cannot_mark_unclaimed_after_claimed(client, auth_headers):
    resp = client.put(f"/api/front-desk/lost-found/{state['item_id']}/mark-unclaimed", headers=auth_headers)
    assert resp.status_code == 400


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/front-desk/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["visitors_today"] >= 1
    assert body["claimed_this_month"] >= 1
