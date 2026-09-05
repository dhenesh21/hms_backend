"""
Birth Register module test: mother patient -> deliver -> register birth
with baby details (including twins) -> issue certificate -> link baby to
a formal patient record.
"""

state = {}


def test_setup_mother_patient(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "Priya",
        "last_name": "Mother",
        "date_of_birth": "1995-06-10",
        "gender": "female",
        "phone": "9123400020",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["mother_id"] = resp.json()["id"]


def test_register_birth_single_baby(client, auth_headers):
    resp = client.post("/api/birth-register", json={
        "mother_patient_id": state["mother_id"],
        "delivery_type": "normal_vaginal",
        "gravida": 2,
        "para": 1,
        "babies": [
            {
                "gender": "female",
                "birth_status": "live_birth",
                "birth_weight_grams": 3200,
                "apgar_score_1min": 8,
                "apgar_score_5min": 9,
            }
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["birth_register_number"].startswith("BR")
    assert len(body["babies"]) == 1
    assert body["babies"][0]["birth_weight_grams"] == 3200
    state["register_id"] = body["id"]
    state["baby_id"] = body["babies"][0]["id"]


def test_register_birth_requires_at_least_one_baby(client, auth_headers):
    resp = client.post("/api/birth-register", json={
        "mother_patient_id": state["mother_id"],
        "babies": [],
    }, headers=auth_headers)
    assert resp.status_code in (400, 422)  # either app-level or pydantic validation


def test_register_twins(client, auth_headers):
    resp = client.post("/api/birth-register", json={
        "mother_patient_id": state["mother_id"],
        "delivery_type": "cesarean",
        "babies": [
            {"gender": "male", "birth_weight_grams": 2400},
            {"gender": "female", "birth_weight_grams": 2350},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["babies"]) == 2
    state["twin_register_id"] = body["id"]


def test_list_birth_registers_by_mother(client, auth_headers):
    resp = client.get(f"/api/birth-register?mother_patient_id={state['mother_id']}", headers=auth_headers)
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert state["register_id"] in ids
    assert state["twin_register_id"] in ids


def test_issue_certificate(client, auth_headers):
    resp = client.put(f"/api/birth-register/babies/{state['baby_id']}/certificate", json={
        "certificate_number": "BC-2026-000123",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["certificate_issued"] is True
    assert body["certificate_number"] == "BC-2026-000123"


def test_cannot_issue_certificate_twice(client, auth_headers):
    resp = client.put(f"/api/birth-register/babies/{state['baby_id']}/certificate", json={
        "certificate_number": "BC-2026-999999",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_link_baby_to_patient_record(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "Baby",
        "last_name": "of Priya",
        "date_of_birth": "2026-08-21",
        "gender": "female",
        "phone": "9123400021",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    baby_patient_id = resp.json()["id"]

    resp = client.put(f"/api/birth-register/babies/{state['baby_id']}/link-patient", json={
        "baby_patient_id": baby_patient_id,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["baby_patient_id"] == baby_patient_id


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/birth-register/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["births_today"] >= 2
    assert body["total_babies_today"] >= 3  # 1 single + 2 twins
    assert body["pending_certificates"] >= 2  # twins' certs not issued yet
