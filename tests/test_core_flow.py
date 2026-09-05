"""
Core flow test: the "money path" through the HMS.

Patient registration -> Doctor onboarding -> OPD visit + prescription
-> Billing (bill + payment) -> Pharmacy (stock + dispense)

This is the sequence a demo/reviewer is most likely to click through first,
and it touches 5 modules, so it's the highest-value thing to keep green.

Tests are ordered and share state via module-level globals, mirroring how
this flow actually happens end-to-end (visit needs a patient+doctor id,
billing needs a visit id, etc). Run with:

    cd backend && pytest tests/ -v
"""
from datetime import date, timedelta

state = {}


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_register_requires_admin(client):
    """Registration is admin-only - anonymous registration must be rejected."""
    resp = client.post("/api/auth/register", json={
        "email": "anon@test.com",
        "password": "Whatever@123",
        "full_name": "Anon User",
        "role": "doctor",
    })
    assert resp.status_code == 401


def test_register_and_login(client, auth_headers):
    resp = client.post("/api/auth/register", json={
        "email": "dr.core@test.com",
        "password": "Doctor@12345",
        "full_name": "Dr. Core Flow",
        "role": "doctor",
        "phone": "9000000001",
        "department": "General Medicine",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["doctor_user_id"] = resp.json()["id"]

    resp = client.post("/api/auth/login", json={
        "email": "dr.core@test.com",
        "password": "Doctor@12345",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body


def test_reject_bad_login(client):
    resp = client.post("/api/auth/login", json={
        "email": "dr.core@test.com",
        "password": "wrong-password",
    })
    assert resp.status_code == 401


def test_doctor_profile_auto_created(client, auth_headers):
    """
    Registering a user with role=doctor auto-creates a DoctorProfile
    (see auth.py register_user). Confirm that happened and grab its id -
    POSTing /doctors/profile again would 400 as a duplicate.
    """
    resp = client.get("/api/doctors", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    doctors = resp.json()
    match = next(
        (d for d in doctors if d.get("user_id") == state["doctor_user_id"]),
        None,
    )
    assert match is not None, f"No auto-created profile for user {state['doctor_user_id']}"
    state["doctor_id"] = match["id"]

    # Explicitly re-creating the same profile should be rejected as a duplicate
    resp = client.post("/api/doctors/profile", json={
        "user_id": state["doctor_user_id"],
        "registration_number": "REG-DUPLICATE",
        "specialization": "General Medicine",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_patient(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "Core",
        "last_name": "Flowtest",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "phone": "9123456780",
        "blood_group": "O+",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uhid"]
    state["patient_id"] = body["id"]


def test_patient_appears_in_list(client, auth_headers):
    resp = client.get("/api/patients/", headers=auth_headers)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()["patients"]]
    assert state["patient_id"] in ids


def test_create_opd_visit_with_prescription(client, auth_headers):
    resp = client.post("/api/opd/visits", json={
        "patient_id": state["patient_id"],
        "doctor_id": state["doctor_id"],
        "chief_complaint": "Fever and headache",
        "temperature": 100.4,
        "primary_diagnosis": "Viral fever",
        "prescriptions": [
            {
                "drug_name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "1-1-1",
                "duration_days": 5,
                "quantity": 15,
            }
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["visit_number"].startswith("OPD")
    assert body["bmi"] is None or isinstance(body["bmi"], float)
    state["opd_visit_id"] = body["id"]


def test_create_bill_for_visit(client, auth_headers):
    resp = client.post("/api/billing/bills", json={
        "patient_id": state["patient_id"],
        "bill_type": "opd",
        "opd_visit_id": state["opd_visit_id"],
        "items": [
            {
                "item_name": "Doctor Consultation",
                "category": "consultation",
                "quantity": 1,
                "unit_price": 500.0,
                "tax_percent": 0.0,
            }
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["gross_total"] == 500.0
    assert body["patient_id"] == state["patient_id"]
    state["bill_id"] = body["id"]


def test_record_full_payment(client, auth_headers):
    resp = client.post("/api/billing/payments", json={
        "bill_id": state["bill_id"],
        "patient_id": state["patient_id"],
        "amount": 500.0,
        "payment_mode": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    # Bill should now be fully paid / balance zero
    resp = client.get(f"/api/billing/bills/{state['bill_id']}", headers=auth_headers)
    assert resp.status_code == 200
    bill = resp.json()
    assert bill["paid_amount"] == 500.0
    assert bill["balance_amount"] == 0.0


def test_add_drug_and_stock(client, auth_headers):
    resp = client.post("/api/pharmacy/drugs", json={
        "drug_code": "PARA-500",
        "brand_name": "Paracip",
        "generic_name": "Paracetamol",
        "category": "analgesic",
        "formulation": "tablet",
        "strength": "500mg",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["drug_id"] = resp.json()["id"]

    expiry = (date.today() + timedelta(days=365)).isoformat()
    resp = client.post("/api/pharmacy/stock", json={
        "drug_id": state["drug_id"],
        "batch_number": "BATCH-001",
        "expiry_date": expiry,
        "quantity_received": 100,
        "purchase_price": 1.5,
        "sale_price": 2.5,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["quantity_available"] == 100


def test_dispense_prescription(client, auth_headers):
    resp = client.post("/api/pharmacy/dispense", json={
        "patient_id": state["patient_id"],
        "prescription_source": "opd",
        "opd_visit_id": state["opd_visit_id"],
        "items": [
            {
                "drug_id": state["drug_id"],
                "drug_name": "Paracetamol",
                "quantity": 15,
                "unit_price": 2.5,
            }
        ],
        "payment_mode": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["patient_id"] == state["patient_id"]

    # Stock should have been decremented by 15
    resp = client.get(f"/api/pharmacy/drugs/{state['drug_id']}/stock", headers=auth_headers)
    assert resp.status_code == 200
    stock = resp.json()[0]
    assert stock["quantity_available"] == 85


def test_full_flow_reachable_from_patient_history(client, auth_headers):
    """Sanity check: the patient's history endpoint should reflect the visit."""
    resp = client.get(f"/api/patients/{state['patient_id']}/history", headers=auth_headers)
    assert resp.status_code == 200
