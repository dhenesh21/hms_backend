"""
Housekeeping module test: verifies cleaning tasks, linen tracking, waste
management, AND the critical cross-module bed lifecycle - a bed discharged
from IPD goes to CLEANING (not straight to AVAILABLE), and only becomes
AVAILABLE again once its housekeeping task is completed.
"""

state = {}


def test_setup_ward_bed_patient_and_doctor(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "Housekeeping",
        "last_name": "TestPatient",
        "date_of_birth": "1980-01-01",
        "gender": "male",
        "phone": "9123406001",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["patient_id"] = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.housekeeping@test.com",
        "password": "Doctor@12345",
        "full_name": "Dr. Housekeeping Test",
        "role": "doctor",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    match = next(d for d in resp.json() if d.get("user_id") == doctor_user_id)
    state["doctor_id"] = match["id"]

    resp = client.post("/api/ipd/wards", json={
        "name": "Housekeeping Test Ward",
        "ward_type": "general",
        "total_beds": 3,
        "available_beds": 3,
        "charge_per_day": 1000.0,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["ward_id"] = resp.json()["id"]

    resp = client.post("/api/ipd/beds", json={
        "bed_number": "HK-TEST-01",
        "ward_id": state["ward_id"],
        "bed_type": "standard",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["bed_id"] = resp.json()["id"]

    resp = client.post("/api/ipd/admissions", json={
        "patient_id": state["patient_id"],
        "bed_id": state["bed_id"],
        "ward_id": state["ward_id"],
        "admitting_doctor_id": state["doctor_id"],
        "admission_type": "elective",
        "chief_complaint": "Routine procedure",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["admission_id"] = resp.json()["id"]


def test_discharge_sets_bed_to_cleaning_not_available(client, auth_headers):
    """The core bug fix this module completes: discharge should NOT make
    the bed immediately available - it must go through cleaning first."""
    resp = client.put(f"/api/ipd/admissions/{state['admission_id']}", json={
        "status": "discharged",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/ipd/wards/{state['ward_id']}/beds", headers=auth_headers)
    assert resp.status_code == 200
    bed = next(b for b in resp.json() if b["id"] == state["bed_id"])
    assert bed["status"] == "cleaning"


def test_bed_not_yet_available_for_new_admission(client, auth_headers):
    resp = client.get("/api/ipd/beds/available", headers=auth_headers)
    ids = [b["id"] for b in resp.json()]
    assert state["bed_id"] not in ids


def test_create_discharge_cleaning_task(client, auth_headers):
    resp = client.post("/api/housekeeping/tasks", json={
        "task_type": "discharge_cleaning",
        "ward_id": state["ward_id"],
        "bed_id": state["bed_id"],
        "notes": "Post-discharge terminal cleaning",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "pending"
    state["task_id"] = resp.json()["id"]


def test_task_appears_in_pending_list(client, auth_headers):
    resp = client.get("/api/housekeeping/tasks/pending", headers=auth_headers)
    ids = [t["id"] for t in resp.json()]
    assert state["task_id"] in ids


def test_start_task(client, auth_headers):
    resp = client.put(f"/api/housekeeping/tasks/{state['task_id']}/start", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "in_progress"


def test_bed_still_in_cleaning_status(client, auth_headers):
    resp = client.get(f"/api/ipd/wards/{state['ward_id']}/beds", headers=auth_headers)
    bed = next(b for b in resp.json() if b["id"] == state["bed_id"])
    assert bed["status"] == "cleaning"


def test_complete_task_frees_bed(client, auth_headers):
    """This is the critical cross-module assertion: completing the
    housekeeping task must flip the bed back to AVAILABLE."""
    resp = client.put(f"/api/housekeeping/tasks/{state['task_id']}/complete", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"

    resp = client.get(f"/api/ipd/wards/{state['ward_id']}/beds", headers=auth_headers)
    bed = next(b for b in resp.json() if b["id"] == state["bed_id"])
    assert bed["status"] == "available"


def test_bed_now_available_for_new_admission(client, auth_headers):
    resp = client.get("/api/ipd/beds/available", headers=auth_headers)
    ids = [b["id"] for b in resp.json()]
    assert state["bed_id"] in ids


def test_verify_task(client, auth_headers):
    resp = client.put(f"/api/housekeeping/tasks/{state['task_id']}/verify", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "verified"
    assert body["verified_at"] is not None


def test_cannot_verify_twice(client, auth_headers):
    resp = client.put(f"/api/housekeeping/tasks/{state['task_id']}/verify", headers=auth_headers)
    assert resp.status_code == 400


def test_linen_send_and_receive(client, auth_headers):
    resp = client.post("/api/housekeeping/linen", json={
        "ward_id": state["ward_id"],
        "item_name": "Bedsheet",
        "quantity_sent": 20,
        "is_soiled": "soiled",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    log_id = resp.json()["id"]

    resp = client.get(f"/api/housekeeping/linen?ward_id={state['ward_id']}&pending_only=true", headers=auth_headers)
    ids = [l["id"] for l in resp.json()]
    assert log_id in ids

    resp = client.put(f"/api/housekeeping/linen/{log_id}/receive", json={"quantity_received": 19}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["quantity_received"] == 19

    resp = client.get(f"/api/housekeeping/linen?ward_id={state['ward_id']}&pending_only=true", headers=auth_headers)
    ids = [l["id"] for l in resp.json()]
    assert log_id not in ids


def test_cannot_receive_linen_twice(client, auth_headers):
    resp = client.post("/api/housekeeping/linen", json={
        "item_name": "Pillow Cover",
        "quantity_sent": 10,
    }, headers=auth_headers)
    log_id = resp.json()["id"]

    client.put(f"/api/housekeeping/linen/{log_id}/receive", json={"quantity_received": 10}, headers=auth_headers)
    resp = client.put(f"/api/housekeeping/linen/{log_id}/receive", json={"quantity_received": 10}, headers=auth_headers)
    assert resp.status_code == 400


def test_biomedical_waste_tracking(client, auth_headers):
    resp = client.post("/api/housekeeping/waste", json={
        "ward_id": state["ward_id"],
        "waste_type": "biomedical",
        "weight_kg": 4.5,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    waste_id = resp.json()["id"]

    resp = client.get("/api/housekeeping/waste?waste_type=biomedical&pending_disposal=true", headers=auth_headers)
    ids = [w["id"] for w in resp.json()]
    assert waste_id in ids

    resp = client.put(f"/api/housekeeping/waste/{waste_id}/dispose", json={
        "disposal_method": "Incineration via licensed vendor",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["disposed_at"] is not None


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/housekeeping/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "pending_tasks" in body
    assert "beds_awaiting_cleaning" in body
