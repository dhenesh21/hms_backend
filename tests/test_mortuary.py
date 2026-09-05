"""
Mortuary module test: death registration -> body storage -> postmortem
(when MLC) -> release -> death certificate.
"""

state = {}


def _create_test_patient(client, auth_headers, suffix):
    resp = client.post("/api/patients/", json={
        "first_name": f"Deceased{suffix}",
        "last_name": "Test",
        "date_of_birth": "1950-01-01",
        "gender": "male",
        "phone": f"9123405{suffix}",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_register_death_non_mlc(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "01")
    resp = client.post("/api/mortuary/records", json={
        "patient_id": patient_id,
        "death_source": "ipd",
        "cause_of_death": "Cardiac arrest",
        "is_mlc": False,
        "storage_unit": "Freezer 1",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["mortuary_number"].startswith("MOR")
    assert body["body_status"] == "in_storage"
    state["record_id"] = body["id"]
    state["patient_id"] = patient_id


def test_duplicate_active_record_rejected(client, auth_headers):
    resp = client.post("/api/mortuary/records", json={
        "patient_id": state["patient_id"],
        "cause_of_death": "duplicate attempt",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_appears_in_storage_list(client, auth_headers):
    resp = client.get("/api/mortuary/records/in-storage", headers=auth_headers)
    ids = [r["id"] for r in resp.json()]
    assert state["record_id"] in ids


def test_release_without_postmortem_requirement(client, auth_headers):
    resp = client.put(f"/api/mortuary/records/{state['record_id']}/release", json={
        "released_to": "Ramesh Kumar",
        "released_relation": "Son",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["body_status"] == "released"
    assert body["release_date"] is not None


def test_no_longer_in_storage_list(client, auth_headers):
    resp = client.get("/api/mortuary/records/in-storage", headers=auth_headers)
    ids = [r["id"] for r in resp.json()]
    assert state["record_id"] not in ids


def test_cannot_release_twice(client, auth_headers):
    resp = client.put(f"/api/mortuary/records/{state['record_id']}/release", json={
        "released_to": "Someone Else",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_issue_death_certificate(client, auth_headers):
    resp = client.put(f"/api/mortuary/records/{state['record_id']}/certificate", json={
        "death_certificate_number": "DC-2026-000456",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["death_certificate_issued"] is True


def test_mlc_case_requires_postmortem_before_release(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "02")
    resp = client.post("/api/mortuary/records", json={
        "patient_id": patient_id,
        "death_source": "emergency",
        "is_mlc": True,
        "postmortem_required": True,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    mlc_record_id = resp.json()["id"]

    # Attempting release before postmortem must be rejected
    resp = client.put(f"/api/mortuary/records/{mlc_record_id}/release", json={
        "released_to": "Family Member",
    }, headers=auth_headers)
    assert resp.status_code == 400

    # Start postmortem
    resp = client.put(f"/api/mortuary/records/{mlc_record_id}/postmortem/start", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["body_status"] == "in_postmortem"

    # Complete postmortem
    resp = client.put(f"/api/mortuary/records/{mlc_record_id}/postmortem/complete", json={
        "postmortem_doctor": "Dr. Forensic",
        "postmortem_findings": "No foul play detected",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["postmortem_done"] is True
    assert body["body_status"] == "in_storage"

    # Now release should succeed
    resp = client.put(f"/api/mortuary/records/{mlc_record_id}/release", json={
        "released_to": "Family Member",
        "released_relation": "Spouse",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["body_status"] == "released"


def test_cannot_start_postmortem_when_not_required(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "03")
    resp = client.post("/api/mortuary/records", json={
        "patient_id": patient_id,
        "postmortem_required": False,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    record_id = resp.json()["id"]

    resp = client.put(f"/api/mortuary/records/{record_id}/postmortem/start", headers=auth_headers)
    assert resp.status_code == 400


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/mortuary/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["deaths_today"] >= 3
    assert body["in_storage"] >= 1
