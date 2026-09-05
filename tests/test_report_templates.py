"""
Tests for Group 1 item #90 (Diagnostic Reporting - standardized templates).
"""

state = {}


def test_create_template(client, auth_headers):
    resp = client.post("/api/report-templates", json={
        "department": "radiology",
        "category": "xray",
        "template_name": "Normal Chest X-Ray",
        "findings_template": "Lungs are clear. Heart size normal. No pleural effusion.",
        "impression_template": "Normal chest X-ray.",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["template_id"] = resp.json()["id"]


def test_list_templates_by_category(client, auth_headers):
    resp = client.get("/api/report-templates?department=radiology&category=xray", headers=auth_headers)
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert state["template_id"] in ids


def test_update_template(client, auth_headers):
    resp = client.put(f"/api/report-templates/{state['template_id']}", json={
        "template_name": "Normal Chest X-Ray (Updated)",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["template_name"] == "Normal Chest X-Ray (Updated)"


def test_radiology_report_records_template_used(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "TemplateTest", "last_name": "Patient",
        "date_of_birth": "1990-01-01", "gender": "male", "phone": "9123411001",
    }, headers=auth_headers)
    patient_id = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.templatetest@test.com", "password": "Doctor@12345",
        "full_name": "Dr Template Test", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    doctor_id = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)

    resp = client.post("/api/radiology/orders", json={
        "patient_id": patient_id, "ordered_by": doctor_id,
        "scan_type": "xray", "body_part": "chest",
    }, headers=auth_headers)
    order_id = resp.json()["id"]

    for target in ["scheduled", "patient_arrived", "in_progress"]:
        client.put(f"/api/radiology/orders/{order_id}/status?status={target}", headers=auth_headers)
    client.post(f"/api/radiology/orders/{order_id}/images", params={
        "file_name": "scan.dcm", "file_path": "/uploads/scan.dcm", "view_type": "pa",
    }, headers=auth_headers)

    resp = client.put(f"/api/radiology/orders/{order_id}/report", json={
        "findings": "Lungs are clear. Heart size normal. No pleural effusion.",
        "impression": "Normal chest X-ray.",
        "report_template_id": state["template_id"],
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["report_template_id"] == state["template_id"]


def test_invalid_template_id_rejected(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "BadTemplate", "last_name": "Patient",
        "date_of_birth": "1990-01-01", "gender": "female", "phone": "9123411002",
    }, headers=auth_headers)
    patient_id = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.badtemplate@test.com", "password": "Doctor@12345",
        "full_name": "Dr Bad Template", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    doctor_id = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)

    resp = client.post("/api/radiology/orders", json={
        "patient_id": patient_id, "ordered_by": doctor_id,
        "scan_type": "xray", "body_part": "hand",
    }, headers=auth_headers)
    order_id = resp.json()["id"]

    for target in ["scheduled", "patient_arrived", "in_progress"]:
        client.put(f"/api/radiology/orders/{order_id}/status?status={target}", headers=auth_headers)
    client.post(f"/api/radiology/orders/{order_id}/images", params={
        "file_name": "scan.dcm", "file_path": "/uploads/scan.dcm", "view_type": "pa",
    }, headers=auth_headers)

    resp = client.put(f"/api/radiology/orders/{order_id}/report", json={
        "findings": "test", "impression": "test",
        "report_template_id": 999999,
    }, headers=auth_headers)
    assert resp.status_code == 404
