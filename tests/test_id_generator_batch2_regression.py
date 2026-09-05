"""
Regression tests for the Group 1 ID-generator race-condition batch fix
across auth.py, doctors.py, hr.py, insurance.py, lab.py, ot.py,
pharmacy.py, and radiology.py.

Each test creates more than 5 records of the same type in a row - past
the threshold where the original bug (create_with_retry always starting
from attempt=1) would have started colliding and crashing.
"""

state = {}


def test_sequential_user_registration_past_five(client, auth_headers):
    """auth.py: employee_id is role-scoped - register 7 nurses in a row."""
    created_ids = []
    for i in range(7):
        resp = client.post("/api/auth/register", json={
            "email": f"nurse.seq{i}@test.com",
            "password": "Nurse@12345",
            "full_name": f"Sequential Nurse {i}",
            "role": "nurse",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        created_ids.append(resp.json()["employee_id"])
    assert len(set(created_ids)) == 7


def test_sequential_appointments_same_doctor_same_day(client, auth_headers):
    """
    doctors.py: this is the deeper fix - token_number previously had NO
    database constraint at all, so proving uniqueness requires actually
    checking the values, not just that no crash happened.
    """
    resp = client.post("/api/patients/", json={
        "first_name": "TokenTest", "last_name": "Patient",
        "date_of_birth": "1990-01-01", "gender": "male", "phone": "9123499001",
    }, headers=auth_headers)
    patient_id = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.tokentest@test.com", "password": "Doctor@12345",
        "full_name": "Dr Token Test", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    doctor_id = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)

    appointment_numbers = []
    token_numbers = []
    for i in range(7):
        resp = client.post("/api/appointments", json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": "2026-09-15",
            "appointment_time": f"{9 + i}:00",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        appointment_numbers.append(resp.json()["appointment_number"])
        token_numbers.append(resp.json()["token_number"])

    assert len(set(appointment_numbers)) == 7
    assert len(set(token_numbers)) == 7


def test_sequential_lab_orders_past_five(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "LabSeq", "last_name": "Patient",
        "date_of_birth": "1990-01-01", "gender": "female", "phone": "9123499002",
    }, headers=auth_headers)
    patient_id = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.labseq@test.com", "password": "Doctor@12345",
        "full_name": "Dr Lab Seq", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    doctor_id = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)

    resp = client.post("/api/lab/tests", json={
        "test_code": "SEQTEST", "test_name": "Sequential Test",
        "category": "biochemistry", "sample_type": "blood",
    }, headers=auth_headers)
    test_id = resp.json()["id"]

    order_numbers = []
    for i in range(7):
        resp = client.post("/api/lab/orders", json={
            "patient_id": patient_id,
            "ordered_by": doctor_id,
            "priority": "routine",
            "test_ids": [test_id],
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        order_numbers.append(resp.json()["order_number"])
    assert len(set(order_numbers)) == 7


def test_sequential_radiology_orders_past_five(client, auth_headers):
    resp = client.post("/api/patients/", json={
        "first_name": "RadSeq", "last_name": "Patient",
        "date_of_birth": "1990-01-01", "gender": "male", "phone": "9123499003",
    }, headers=auth_headers)
    patient_id = resp.json()["id"]

    resp = client.post("/api/auth/register", json={
        "email": "dr.radseq@test.com", "password": "Doctor@12345",
        "full_name": "Dr Rad Seq", "role": "doctor",
    }, headers=auth_headers)
    doctor_user_id = resp.json()["id"]
    resp = client.get("/api/doctors", headers=auth_headers)
    doctor_id = next(d["id"] for d in resp.json() if d.get("user_id") == doctor_user_id)

    order_numbers = []
    for i in range(7):
        resp = client.post("/api/radiology/orders", json={
            "patient_id": patient_id,
            "ordered_by": doctor_id,
            "scan_type": "xray",
            "body_part": "chest",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        order_numbers.append(resp.json()["order_number"])
    assert len(set(order_numbers)) == 7
