"""
CSSD module test: receive dirty instruments -> sterilize -> quality check
(pass/fail) -> dispatch.
"""

state = {}


def test_receive_items(client, auth_headers):
    resp = client.post("/api/cssd/cycles", json={
        "item_set_name": "General Surgery Set A",
        "quantity": 1,
        "source_department": "OT-1",
        "method": "autoclave",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cycle_number"].startswith("CSSD")
    assert body["status"] == "received"
    state["cycle_id"] = body["id"]


def test_appears_in_active_cycles(client, auth_headers):
    resp = client.get("/api/cssd/cycles/active", headers=auth_headers)
    ids = [c["id"] for c in resp.json()]
    assert state["cycle_id"] in ids


def test_start_sterilization(client, auth_headers):
    resp = client.put(f"/api/cssd/cycles/{state['cycle_id']}/start-sterilization", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sterilizing"
    assert body["sterilization_start"] is not None


def test_quality_check_pass(client, auth_headers):
    resp = client.put(f"/api/cssd/cycles/{state['cycle_id']}/quality-check", json={
        "passed": True,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["quality_check_passed"] == "pass"


def test_dispatch_cycle(client, auth_headers):
    resp = client.put(f"/api/cssd/cycles/{state['cycle_id']}/dispatch", json={
        "dispatched_to": "OT-1",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "dispatched"
    assert body["dispatched_to"] == "OT-1"


def test_dispatched_not_in_active_cycles(client, auth_headers):
    resp = client.get("/api/cssd/cycles/active", headers=auth_headers)
    ids = [c["id"] for c in resp.json()]
    assert state["cycle_id"] not in ids


def test_failed_quality_check(client, auth_headers):
    resp = client.post("/api/cssd/cycles", json={
        "item_set_name": "Orthopedic Set B",
        "source_department": "OT-2",
    }, headers=auth_headers)
    cycle_id = resp.json()["id"]

    client.put(f"/api/cssd/cycles/{cycle_id}/start-sterilization", headers=auth_headers)
    resp = client.put(f"/api/cssd/cycles/{cycle_id}/quality-check", json={
        "passed": False,
        "notes": "Biological indicator failed",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"


def test_cannot_dispatch_failed_cycle(client, auth_headers):
    resp = client.post("/api/cssd/cycles", json={"item_set_name": "Test Set"}, headers=auth_headers)
    cycle_id = resp.json()["id"]
    client.put(f"/api/cssd/cycles/{cycle_id}/start-sterilization", headers=auth_headers)
    client.put(f"/api/cssd/cycles/{cycle_id}/quality-check", json={"passed": False}, headers=auth_headers)

    resp = client.put(f"/api/cssd/cycles/{cycle_id}/dispatch", json={"dispatched_to": "Ward 3"}, headers=auth_headers)
    assert resp.status_code == 400


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/cssd/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["dispatched_today"] >= 1
    assert body["failed_cycles"] >= 1
