"""
Diet module test - verifies the API matches the frontend's dietService
contract exactly: getChart is keyed by ADMISSION id (not chart id), and
meal actions live under /diet-charts/meals/{id}/serve|consume.
"""

state = {}


def test_create_diet_chart(client, auth_headers):
    resp = client.post("/api/diet-charts", json={
        "admission_id": 501,
        "patient_id": 1,
        "diet_type": "diabetic",
        "special_instructions": "No added sugar",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["diet_type"] == "diabetic"
    state["chart_id"] = body["id"]


def test_get_chart_by_admission_id(client, auth_headers):
    """This is the key contract: frontend calls getChart(admissionId), not chartId."""
    resp = client.get("/api/diet-charts/501", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == state["chart_id"]
    assert body["admission_id"] == 501


def test_add_meal_and_mark_served_consumed(client, auth_headers):
    resp = client.post(f"/api/diet-charts/{state['chart_id']}/meals", json={
        "meal_type": "lunch",
        "items": "Rice, dal, vegetable",
        "calories": 450,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    meal_id = resp.json()["id"]

    resp = client.put(f"/api/diet-charts/meals/{meal_id}/serve", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    resp = client.put(f"/api/diet-charts/meals/{meal_id}/consume", json={"consumed": True}, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/diet-charts/501", headers=auth_headers)
    meal = resp.json()["meals"][0]
    assert meal["served"] is True
    assert meal["consumed"] is True


def test_diet_template(client, auth_headers):
    resp = client.get("/api/diet-charts/templates/diabetic", headers=auth_headers)
    assert resp.status_code == 200
    assert "description" in resp.json()
