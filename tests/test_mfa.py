"""
Tests for Group 1 item #8 (Auth/MFA - real TOTP 2FA) and the token-type
security fix that came with it.
"""
import pyotp

state = {}


def test_setup_mfa_test_user(client, auth_headers):
    resp = client.post("/api/auth/register", json={
        "email": "mfa.testuser@test.com",
        "password": "MfaUser@12345",
        "full_name": "MFA Test User",
        "role": "receptionist",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text

    resp = client.post("/api/auth/login", json={
        "email": "mfa.testuser@test.com", "password": "MfaUser@12345",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    state["access_token"] = body["access_token"]
    state["user_headers"] = {"Authorization": f"Bearer {body['access_token']}"}


def test_mfa_setup_returns_secret_and_qr(client):
    resp = client.post("/api/auth/mfa/setup", headers=state["user_headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["secret"]) >= 16
    assert body["qr_code"].startswith("data:image/png;base64,")
    assert "otpauth://" in body["otpauth_uri"]
    state["secret"] = body["secret"]


def test_mfa_setup_twice_before_confirm_is_allowed_to_regenerate(client):
    resp = client.post("/api/auth/mfa/setup", headers=state["user_headers"])
    assert resp.status_code == 200
    state["secret"] = resp.json()["secret"]


def test_confirm_with_wrong_code_rejected(client):
    resp = client.post("/api/auth/mfa/confirm", json={"code": "000000"}, headers=state["user_headers"])
    assert resp.status_code == 400


def test_confirm_with_correct_code_enables_mfa(client):
    totp = pyotp.TOTP(state["secret"])
    code = totp.now()
    resp = client.post("/api/auth/mfa/confirm", json={"code": code}, headers=state["user_headers"])
    assert resp.status_code == 200, resp.text


def test_setup_again_after_enabled_is_rejected(client):
    resp = client.post("/api/auth/mfa/setup", headers=state["user_headers"])
    assert resp.status_code == 400


def test_login_now_requires_mfa_step(client):
    resp = client.post("/api/auth/login", json={
        "email": "mfa.testuser@test.com", "password": "MfaUser@12345",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mfa_required"] is True
    assert "mfa_token" in body
    assert "access_token" not in body
    state["mfa_token"] = body["mfa_token"]


def test_mfa_pending_token_cannot_authenticate_api_calls(client):
    resp = client.get("/api/patients/", headers={"Authorization": f"Bearer {state['mfa_token']}"})
    assert resp.status_code == 401


def test_mfa_verify_login_with_wrong_code_rejected(client):
    resp = client.post("/api/auth/mfa/verify-login", json={
        "mfa_token": state["mfa_token"], "code": "000000",
    })
    assert resp.status_code == 401


def test_mfa_verify_login_with_correct_code_issues_real_tokens(client):
    totp = pyotp.TOTP(state["secret"])
    code = totp.now()
    resp = client.post("/api/auth/mfa/verify-login", json={
        "mfa_token": state["mfa_token"], "code": code,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    state["real_access_token"] = body["access_token"]
    state["real_refresh_token"] = body["refresh_token"]


def test_refresh_token_cannot_be_used_as_bearer_access_token(client):
    resp = client.get("/api/patients/", headers={"Authorization": f"Bearer {state['real_refresh_token']}"})
    assert resp.status_code == 401


def test_real_access_token_works_normally(client):
    resp = client.get("/api/patients/", headers={"Authorization": f"Bearer {state['real_access_token']}"})
    assert resp.status_code == 200


def test_disable_mfa_requires_both_password_and_code(client):
    user_headers = {"Authorization": f"Bearer {state['real_access_token']}"}
    totp = pyotp.TOTP(state["secret"])

    resp = client.post("/api/auth/mfa/disable", json={
        "password": "WrongPassword123", "code": totp.now(),
    }, headers=user_headers)
    assert resp.status_code == 401

    resp = client.post("/api/auth/mfa/disable", json={
        "password": "MfaUser@12345", "code": "000000",
    }, headers=user_headers)
    assert resp.status_code == 401

    resp = client.post("/api/auth/mfa/disable", json={
        "password": "MfaUser@12345", "code": totp.now(),
    }, headers=user_headers)
    assert resp.status_code == 200, resp.text


def test_login_no_longer_requires_mfa_after_disable(client):
    resp = client.post("/api/auth/login", json={
        "email": "mfa.testuser@test.com", "password": "MfaUser@12345",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
