"""
Critical Care module test: IPD admission -> critical care admission
-> monitoring rounds -> step-down back to general ward.
"""

state = {}


def test_setup_patient_and_ipd_admission(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "Critical",
        "last_name": "CareTest",
        "date_of_birth": "1970-01-01",
        "gender": "female",
        "phone": "9123400001",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["patient_id"] = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.critical@test.com",
        "password": "Doctor@12345",
        "full_name": "Dr. Critical Care",
        "role": "doctor",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    doctor_user_id = resp.json()["id"]

    resp = client.get("/api/doctors", headers=auth_headers)
    assert resp.status_code == 200
    match = next(d for d in resp.json() if d.get("user_id") == doctor_user_id)
    state["doctor_id"] = match["id"]

    resp = client.post("/api/ipd/wards", json={
        "name": "ICU Ward A",
        "ward_type": "icu",
        "total_beds": 5,
        "available_beds": 5,
        "charge_per_day": 5000.0,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["ward_id"] = resp.json()["id"]

    resp = client.post("/api/ipd/beds", json={
        "bed_number": "ICU-A-01",
        "ward_id": state["ward_id"],
        "bed_type": "icu",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["bed_id"] = resp.json()["id"]

    resp = client.post("/api/ipd/admissions", json={
        "patient_id": state["patient_id"],
        "bed_id": state["bed_id"],
        "ward_id": state["ward_id"],
        "admitting_doctor_id": state["doctor_id"],
        "admission_type": "emergency",
        "chief_complaint": "Severe sepsis",
        "diagnosis_at_admission": "Septic shock",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["ipd_admission_id"] = resp.json()["id"]


def test_admit_to_critical_care(client, auth_headers):
    resp = client.post("/api/critical-care/admissions", json={
        "ipd_admission_id": state["ipd_admission_id"],
        "unit_type": "icu",
        "admission_reason": "Septic shock, hemodynamic instability",
        "code_status": "full_code",
        "on_ventilator": True,
        "central_line": True,
        "central_line_site": "Right subclavian",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["unit_type"] == "icu"
    assert body["on_ventilator"] is True
    assert body["is_active"] is True
    state["cc_admission_id"] = body["id"]


def test_duplicate_active_admission_rejected(client, auth_headers):
    resp = client.post("/api/critical-care/admissions", json={
        "ipd_admission_id": state["ipd_admission_id"],
        "unit_type": "icu",
        "admission_reason": "duplicate attempt",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_appears_in_active_list(client, auth_headers):
    resp = client.get("/api/critical-care/admissions?unit_type=icu", headers=auth_headers)
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()]
    assert state["cc_admission_id"] in ids


def test_add_monitoring_rounds(client, auth_headers):
    resp = client.post(f"/api/critical-care/admissions/{state['cc_admission_id']}/rounds", json={
        "heart_rate": 110,
        "blood_pressure_systolic": 88,
        "blood_pressure_diastolic": 55,
        "oxygen_saturation": 94.0,
        "ventilator_mode": "SIMV",
        "fio2_percent": 60.0,
        "peep": 8.0,
        "inotropes": "Noradrenaline 0.15 mcg/kg/min",
        "sedation_score": -2,
        "gcs_score": 10,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/critical-care/admissions/{state['cc_admission_id']}/rounds", headers=auth_headers)
    assert resp.status_code == 200
    rounds = resp.json()
    assert len(rounds) == 1
    assert rounds[0]["inotropes"] == "Noradrenaline 0.15 mcg/kg/min"


def test_update_ventilator_status(client, auth_headers):
    resp = client.put(f"/api/critical-care/admissions/{state['cc_admission_id']}", json={
        "on_ventilator": False,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["on_ventilator"] is False


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/critical-care/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_active"] >= 1
    assert body["by_unit"]["icu"] >= 1


def test_step_down(client, auth_headers):
    resp = client.post(f"/api/critical-care/admissions/{state['cc_admission_id']}/step-down", json={
        "step_down_notes": "Hemodynamically stable, moved to general ward",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_active"] is False
    assert body["stepped_down_at"] is not None


def test_cannot_add_rounds_after_step_down(client, auth_headers):
    resp = client.post(f"/api/critical-care/admissions/{state['cc_admission_id']}/rounds", json={
        "heart_rate": 80,
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_stepped_down_not_in_active_list(client, auth_headers):
    resp = client.get("/api/critical-care/admissions?unit_type=icu", headers=auth_headers)
    ids = [a["id"] for a in resp.json()]
    assert state["cc_admission_id"] not in ids

    resp = client.get("/api/critical-care/admissions?active_only=false", headers=auth_headers)
    ids = [a["id"] for a in resp.json()]
    assert state["cc_admission_id"] in ids


def test_readmit_after_step_down_allowed(client, auth_headers):
    """A new critical care episode should be allowed after a previous one was stepped down."""
    resp = client.post("/api/critical-care/admissions", json={
        "ipd_admission_id": state["ipd_admission_id"],
        "unit_type": "ccu",
        "admission_reason": "Relapse - new arrhythmia",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
