"""
Tests for Group 1 item #85 (RIS - real workflow, not just order+report):
status state-machine validation, technologist/equipment assignment,
separated report-submit vs approve actions, and critical finding
escalation.
"""

state = {}


def test_setup_patient_and_doctor(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "RIS", "last_name": "TestPatient",
        "date_of_birth": "1988-01-01", "gender": "female", "phone": "9123410001",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["patient_id"] = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.ristest@test.com", "password": "Doctor@12345",
        "full_name": "Dr RIS Test", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    state["doctor_id"] = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)


def test_create_order_starts_in_ordered_status(client, auth_headers):
    resp = client.post("/api/radiology/orders", json={
        "patient_id": state["patient_id"],
        "ordered_by": state["doctor_id"],
        "scan_type": "ct",
        "body_part": "chest",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "ordered"
    state["order_id"] = body["id"]


def test_cannot_skip_straight_to_approved(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/status?status=approved", headers=auth_headers)
    assert resp.status_code == 400


def test_cannot_move_backwards(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/status?status=in_progress", headers=auth_headers)
    assert resp.status_code == 400


def test_valid_forward_transitions(client, auth_headers):
    for target in ["scheduled", "patient_arrived", "in_progress"]:
        resp = client.put(f"/api/radiology/orders/{state['order_id']}/status?status={target}", headers=auth_headers)
        assert resp.status_code == 200, f"{target}: {resp.text}"


def test_assign_technologist_and_equipment(client, auth_headers):
    resp = client.post("/api/facility/equipment", json={
        "asset_code": "CT-RIS-TEST", "name": "CT Scanner (RIS test)",
    }, headers=auth_headers)
    equipment_id = resp.json()["id"]

    resp = client.put(f"/api/radiology/orders/{state['order_id']}/assign", json={
        "performed_by": 1,
        "equipment_id": equipment_id,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["equipment_id"] == equipment_id


def test_upload_image_moves_to_images_uploaded(client, auth_headers):
    resp = client.post(f"/api/radiology/orders/{state['order_id']}/images", params={
        "file_name": "scan1.dcm", "file_path": "/uploads/scan1.dcm", "view_type": "axial",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/radiology/orders/{state['order_id']}", headers=auth_headers)
    assert resp.json()["status"] == "images_uploaded"


def test_cannot_approve_before_report(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/approve", headers=auth_headers)
    assert resp.status_code == 400


def test_submit_report_only_sets_reported_not_approved(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/report", json={
        "findings": "No acute abnormality",
        "impression": "Normal chest CT",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "reported"
    assert body["approved_at"] is None


def test_approve_report_now_works(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/approve", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_at"] is not None


def test_status_setter_rejects_anything_from_terminal_approved(client, auth_headers):
    resp = client.put(f"/api/radiology/orders/{state['order_id']}/status?status=reported", headers=auth_headers)
    assert resp.status_code == 400


def test_critical_finding_flow(client, auth_headers):
    resp = client.post("/api/radiology/orders", json={
        "patient_id": state["patient_id"],
        "ordered_by": state["doctor_id"],
        "scan_type": "mri",
        "body_part": "brain",
    }, headers=auth_headers)
    critical_order_id = resp.json()["id"]

    resp = client.put(f"/api/radiology/orders/{critical_order_id}/flag-critical", json={
        "notes": "Possible acute hemorrhage - needs immediate review",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_critical_finding"] is True
    assert body["critical_finding_acknowledged_at"] is None

    resp = client.get("/api/radiology/orders/critical", headers=auth_headers)
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert critical_order_id in ids

    resp = client.put(f"/api/radiology/orders/{critical_order_id}/acknowledge-critical", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["critical_finding_acknowledged_at"] is not None

    resp = client.get("/api/radiology/orders/critical?unacknowledged_only=true", headers=auth_headers)
    ids = [o["id"] for o in resp.json()]
    assert critical_order_id not in ids


def test_cannot_acknowledge_twice(client, auth_headers):
    resp = client.post("/api/radiology/orders", json={
        "patient_id": state["patient_id"],
        "ordered_by": state["doctor_id"],
        "scan_type": "xray",
        "body_part": "hand",
    }, headers=auth_headers)
    order_id = resp.json()["id"]

    client.put(f"/api/radiology/orders/{order_id}/flag-critical", json={"notes": "test"}, headers=auth_headers)
    client.put(f"/api/radiology/orders/{order_id}/acknowledge-critical", headers=auth_headers)
    resp = client.put(f"/api/radiology/orders/{order_id}/acknowledge-critical", headers=auth_headers)
    assert resp.status_code == 400


def test_cannot_flag_critical_without_notes(client, auth_headers):
    resp = client.post("/api/radiology/orders", json={
        "patient_id": state["patient_id"],
        "ordered_by": state["doctor_id"],
        "scan_type": "xray",
        "body_part": "foot",
    }, headers=auth_headers)
    order_id = resp.json()["id"]
    resp = client.put(f"/api/radiology/orders/{order_id}/flag-critical", json={}, headers=auth_headers)
    assert resp.status_code == 422
