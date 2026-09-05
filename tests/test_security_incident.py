"""
Security Incident Management module test: report -> investigate -> resolve.
"""

state = {}


def test_report_incident(client, auth_headers):
    resp = client.post("/api/security-incidents", json={
        "incident_type": "unauthorized_access",
        "severity": "high",
        "location": "Pharmacy Store Room",
        "description": "Unidentified person found in restricted storage area",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["incident_number"].startswith("SEC")
    assert body["status"] == "reported"
    state["incident_id"] = body["id"]


def test_update_to_under_investigation(client, auth_headers):
    resp = client.put(f"/api/security-incidents/{state['incident_id']}", json={
        "status": "under_investigation",
        "investigated_by": "Head of Security",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "under_investigation"


def test_resolve_incident(client, auth_headers):
    resp = client.put(f"/api/security-incidents/{state['incident_id']}", json={
        "status": "resolved",
        "investigation_notes": "CCTV review showed maintenance contractor with valid access",
        "resolution": "False alarm - access was authorized, badge system updated",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None


def test_cannot_update_closed_incident(client, auth_headers):
    resp = client.post("/api/security-incidents", json={
        "location": "Test",
        "description": "Test incident",
    }, headers=auth_headers)
    incident_id = resp.json()["id"]

    client.put(f"/api/security-incidents/{incident_id}", json={"status": "closed"}, headers=auth_headers)
    resp = client.put(f"/api/security-incidents/{incident_id}", json={"status": "resolved"}, headers=auth_headers)
    assert resp.status_code == 400


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/security-incidents/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["incidents_this_month"] >= 2
