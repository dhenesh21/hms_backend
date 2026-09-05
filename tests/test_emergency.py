"""
Emergency module test: ER registration -> triage -> treatment -> discharge,
plus the MLC register and dashboard stats views.
"""

state = {}


def _create_test_patient(client, auth_headers, suffix=""):
    resp = client.post("/api/patients/", json={
        "first_name": f"ER{suffix}",
        "last_name": "Patient",
        "date_of_birth": "1985-01-01",
        "gender": "male",
        "phone": f"91234567{suffix or '00'}",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_register_er_visit_with_triage(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "01")
    state["patient_id"] = patient_id

    resp = client.post("/api/emergency/visits", json={
        "patient_id": patient_id,
        "arrival_mode": "ambulance",
        "brought_by": "City Ambulance Service",
        "chief_complaint": "Road traffic accident, head injury",
        "is_mlc": True,
        "is_trauma": True,
        "incident_type": "RTA",
        "police_informed": True,
        "police_station": "Coimbatore North PS",
        "triage": {
            "triage_level": "level_1_resuscitation",
            "pulse_rate": 120,
            "blood_pressure_systolic": 90,
            "blood_pressure_diastolic": 60,
            "oxygen_saturation": 92.0,
            "glasgow_coma_scale": 12,
            "pain_score": 8,
        },
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["er_number"].startswith("ER")
    assert body["status"] == "in_triage"
    assert body["is_mlc"] is True
    assert body["triage"]["triage_level"] == "level_1_resuscitation"
    state["er_visit_id"] = body["id"]


def test_visit_appears_in_active_queue(client, auth_headers):
    resp = client.get("/api/emergency/visits/active", headers=auth_headers)
    assert resp.status_code == 200
    ids = [v["id"] for v in resp.json()]
    assert state["er_visit_id"] in ids


def test_duplicate_triage_rejected(client, auth_headers):
    resp = client.post(f"/api/emergency/visits/{state['er_visit_id']}/triage", json={
        "triage_level": "level_2_emergent",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_add_treatment(client, auth_headers):
    resp = client.post(f"/api/emergency/visits/{state['er_visit_id']}/treatments", json={
        "treatment_given": "IV fluids, oxygen support",
        "medication_given": "Normal saline 500ml",
        "procedure_performed": "IV cannulation",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/emergency/visits/{state['er_visit_id']}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_treatment"
    assert len(body["treatments"]) == 1


def test_discharge_sets_discharge_time(client, auth_headers):
    resp = client.put(f"/api/emergency/visits/{state['er_visit_id']}", json={
        "status": "discharged",
        "outcome_notes": "Stable, discharged with advice",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "discharged"
    assert body["discharge_time"] is not None


def test_visit_no_longer_in_active_queue(client, auth_headers):
    resp = client.get("/api/emergency/visits/active", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["er_visit_id"] not in ids


def test_mlc_register_contains_visit(client, auth_headers):
    resp = client.get("/api/emergency/mlc-register", headers=auth_headers)
    assert resp.status_code == 200
    ids = [v["id"] for v in resp.json()]
    assert state["er_visit_id"] in ids


def test_non_mlc_visit_excluded_from_register(client, auth_headers):
    patient_id = _create_test_patient(client, auth_headers, "02")
    resp = client.post("/api/emergency/visits", json={
        "patient_id": patient_id,
        "arrival_mode": "walk_in",
        "chief_complaint": "High fever",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    walkin_id = resp.json()["id"]

    resp = client.get("/api/emergency/mlc-register", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert walkin_id not in ids


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/emergency/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_visits_today"] >= 2
    assert body["mlc_cases_today"] >= 1
