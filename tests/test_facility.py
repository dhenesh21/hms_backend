"""
Facility & Equipment module test: equipment registration, maintenance
logging (status transitions), and facility service requests.
"""

state = {}


def test_register_equipment(client, auth_headers):
    resp = client.post("/api/facility/equipment", json={
        "asset_code": "VENT-001",
        "name": "ICU Ventilator",
        "category": "Ventilator",
        "manufacturer": "MedTech Inc",
        "department": "ICU",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "operational"
    state["equipment_id"] = body["id"]


def test_duplicate_asset_code_rejected(client, auth_headers):
    resp = client.post("/api/facility/equipment", json={
        "asset_code": "VENT-001",
        "name": "Duplicate Ventilator",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_mark_under_maintenance(client, auth_headers):
    resp = client.put(f"/api/facility/equipment/{state['equipment_id']}", json={
        "status": "under_maintenance",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "under_maintenance"


def test_appears_in_maintenance_filter(client, auth_headers):
    resp = client.get("/api/facility/equipment?status=under_maintenance", headers=auth_headers)
    ids = [e["id"] for e in resp.json()]
    assert state["equipment_id"] in ids


def test_log_maintenance_restores_operational(client, auth_headers):
    resp = client.post(f"/api/facility/equipment/{state['equipment_id']}/maintenance", json={
        "maintenance_type": "corrective",
        "description": "Replaced faulty sensor",
        "performed_by": "TechCorp Services",
        "cost": 1500.0,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/facility/equipment/{state['equipment_id']}", headers=auth_headers)
    assert resp.json()["status"] == "operational"


def test_maintenance_history_recorded(client, auth_headers):
    resp = client.get(f"/api/facility/equipment/{state['equipment_id']}/maintenance", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_service_request(client, auth_headers):
    resp = client.post("/api/facility/service-requests", json={
        "category": "Electrical",
        "description": "AC not cooling in Ward 3B",
        "location": "Ward 3B",
        "priority": "high",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["request_number"].startswith("FSR")
    assert body["status"] == "open"
    state["request_id"] = body["id"]


def test_resolve_service_request(client, auth_headers):
    resp = client.put(f"/api/facility/service-requests/{state['request_id']}", json={
        "status": "resolved",
        "assigned_to": "Facilities Team",
        "resolution_notes": "Compressor recharged",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/facility/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_equipment"] >= 1
