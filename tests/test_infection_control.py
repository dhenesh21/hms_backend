"""
Infection Control module test: report infection incident -> start isolation
precaution -> resolve incident -> end isolation.
"""

state = {}


def _create_test_patient(client, auth_headers, suffix):
    resp = client.post("/api/patients/", json={
        "first_name": f"Infection{suffix}",
        "last_name": "TestPatient",
        "date_of_birth": "1975-01-01",
        "gender": "female",
        "phone": f"9123407{suffix}",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_report_infection_incident(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "01")
    state["patient_id"] = patient_id

    resp = client.post("/api/infection-control/incidents", json={
        "patient_id": patient_id,
        "infection_type": "MRSA",
        "source": "hospital_acquired",
        "symptoms": "Fever, wound discharge",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["incident_number"].startswith("INF")
    assert body["status"] == "reported"
    state["incident_id"] = body["id"]


def test_start_isolation_precaution(client, auth_headers):
    resp = client.post("/api/infection-control/isolation", json={
        "patient_id": state["patient_id"],
        "infection_incident_id": state["incident_id"],
        "precaution_type": "contact",
        "reason": "MRSA - contact precautions required",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_active"] is True
    state["isolation_id"] = body["id"]


def test_duplicate_active_isolation_rejected(client, auth_headers):
    resp = client.post("/api/infection-control/isolation", json={
        "patient_id": state["patient_id"],
        "precaution_type": "droplet",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_isolation_appears_in_active_list(client, auth_headers):
    resp = client.get("/api/infection-control/isolation", headers=auth_headers)
    ids = [i["id"] for i in resp.json()]
    assert state["isolation_id"] in ids


def test_update_incident_to_under_investigation(client, auth_headers):
    resp = client.put(f"/api/infection-control/incidents/{state['incident_id']}", json={
        "status": "under_investigation",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "under_investigation"


def test_resolve_incident_sets_resolved_date(client, auth_headers):
    resp = client.put(f"/api/infection-control/incidents/{state['incident_id']}", json={
        "status": "resolved",
        "corrective_action": "Contact precautions enforced, wound care protocol followed",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolved_date"] is not None


def test_end_isolation(client, auth_headers):
    resp = client.put(f"/api/infection-control/isolation/{state['isolation_id']}/end", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_active"] is False
    assert body["ended_at"] is not None


def test_cannot_end_isolation_twice(client, auth_headers):
    resp = client.put(f"/api/infection-control/isolation/{state['isolation_id']}/end", headers=auth_headers)
    assert resp.status_code == 400


def test_isolation_no_longer_in_active_list(client, auth_headers):
    resp = client.get("/api/infection-control/isolation", headers=auth_headers)
    ids = [i["id"] for i in resp.json()]
    assert state["isolation_id"] not in ids


def test_new_isolation_allowed_after_previous_ended(client, auth_headers):
    """A patient can get a new isolation episode once the previous one ended."""
    resp = client.post("/api/infection-control/isolation", json={
        "patient_id": state["patient_id"],
        "precaution_type": "standard",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/infection-control/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["incidents_this_month"] >= 1
    assert body["hospital_acquired_this_month"] >= 1
    assert body["active_isolations"] >= 1
