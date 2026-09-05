"""
Ambulance module test: vehicle + driver setup -> trip request -> dispatch
-> complete, plus fuel/maintenance logs and GPS location updates.
"""

state = {}


def test_create_vehicle(client, auth_headers):
    resp = client.post("/api/ambulance/vehicles", json={
        "vehicle_number": "TN-38-AB-1234",
        "vehicle_type": "advanced_life_support",
        "make_model": "Force Traveller",
        "year": 2022,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "available"
    state["vehicle_id"] = body["id"]


def test_duplicate_vehicle_number_rejected(client, auth_headers):
    resp = client.post("/api/ambulance/vehicles", json={
        "vehicle_number": "TN-38-AB-1234",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_driver(client, auth_headers):
    resp = client.post("/api/ambulance/drivers", json={
        "name": "Ravi Kumar",
        "phone": "9876543210",
        "license_number": "TN38-2020-0012345",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    state["driver_id"] = resp.json()["id"]


def test_request_trip(client, auth_headers):
    resp = client.post("/api/ambulance/trips", json={
        "vehicle_id": state["vehicle_id"],
        "driver_id": state["driver_id"],
        "trip_type": "emergency_pickup",
        "pickup_location": "123 Anna Nagar, Coimbatore",
        "caller_name": "Neighbor",
        "caller_phone": "9123456789",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["trip_number"].startswith("AMB")
    assert body["status"] == "requested"
    state["trip_id"] = body["id"]


def test_vehicle_now_on_trip(client, auth_headers):
    resp = client.get("/api/ambulance/vehicles?status=on_trip", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["vehicle_id"] in ids


def test_cannot_request_second_trip_on_busy_vehicle(client, auth_headers):
    resp = client.post("/api/ambulance/trips", json={
        "vehicle_id": state["vehicle_id"],
        "pickup_location": "Another location",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_trip_appears_in_active_list(client, auth_headers):
    resp = client.get("/api/ambulance/trips/active", headers=auth_headers)
    ids = [t["id"] for t in resp.json()]
    assert state["trip_id"] in ids


def test_dispatch_trip(client, auth_headers):
    resp = client.put(f"/api/ambulance/trips/{state['trip_id']}/dispatch", json={
        "drop_location": "City Hospital ER",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "dispatched"
    assert body["dispatched_at"] is not None


def test_cannot_dispatch_twice(client, auth_headers):
    resp = client.put(f"/api/ambulance/trips/{state['trip_id']}/dispatch", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_update_gps_location(client, auth_headers):
    resp = client.put(f"/api/ambulance/vehicles/{state['vehicle_id']}/location", json={
        "latitude": 11.0168,
        "longitude": 76.9558,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_latitude"] == 11.0168
    assert body["location_updated_at"] is not None


def test_complete_trip(client, auth_headers):
    resp = client.put(f"/api/ambulance/trips/{state['trip_id']}/complete", json={
        "distance_km": 8.5,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["distance_km"] == 8.5


def test_vehicle_available_again_after_completion(client, auth_headers):
    resp = client.get("/api/ambulance/vehicles?status=available", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["vehicle_id"] in ids


def test_completed_trip_not_in_active_list(client, auth_headers):
    resp = client.get("/api/ambulance/trips/active", headers=auth_headers)
    ids = [t["id"] for t in resp.json()]
    assert state["trip_id"] not in ids


def test_add_fuel_log(client, auth_headers):
    resp = client.post("/api/ambulance/fuel-logs", json={
        "vehicle_id": state["vehicle_id"],
        "liters": 40.0,
        "cost": 3600.0,
        "odometer_reading": 45210,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/ambulance/fuel-logs?vehicle_id={state['vehicle_id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_add_maintenance_log_sets_vehicle_to_maintenance(client, auth_headers):
    resp = client.post("/api/ambulance/maintenance-logs", json={
        "vehicle_id": state["vehicle_id"],
        "description": "Brake pad replacement",
        "cost": 2500.0,
        "performed_by": "City Auto Works",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get("/api/ambulance/vehicles?status=maintenance", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert state["vehicle_id"] in ids


def test_cancel_trip_frees_vehicle(client, auth_headers):
    resp = client.post("/api/ambulance/vehicles", json={"vehicle_number": "TN-38-CD-5678"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    vehicle2_id = resp.json()["id"]

    resp = client.post("/api/ambulance/trips", json={
        "vehicle_id": vehicle2_id,
        "pickup_location": "Test location",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    trip2_id = resp.json()["id"]

    resp = client.put(f"/api/ambulance/trips/{trip2_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"

    resp = client.get("/api/ambulance/vehicles?status=available", headers=auth_headers)
    ids = [v["id"] for v in resp.json()]
    assert vehicle2_id in ids


def test_cannot_cancel_completed_trip(client, auth_headers):
    resp = client.put(f"/api/ambulance/trips/{state['trip_id']}/cancel", headers=auth_headers)
    assert resp.status_code == 400


def test_dashboard_stats(client, auth_headers):
    resp = client.get("/api/ambulance/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_vehicles"] >= 1
    assert body["trips_today"] >= 1
