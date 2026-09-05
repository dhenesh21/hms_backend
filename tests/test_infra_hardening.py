"""
Tests for Group 6 infrastructure hardening: health/readiness checks and
rate limiting.

The rate-limit test deliberately does NOT hammer the real /api/auth/login
endpoint in a loop: that endpoint's limiter state is shared (in-memory,
keyed by client IP) across the whole test session, and other tests rely
on a session-scoped admin_token fixture that calls login. Exhausting the
quota here would make unrelated tests fail depending on execution order.
Instead, the blocking behavior is proven against an isolated mini-app
with its own Limiter instance, and the real login endpoint is only
exercised a couple of times (well under its 10/minute limit) to confirm
the decorator didn't break normal login.
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.main import check_database_connection


def test_health_liveness_always_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_health_readiness_reports_connected_db(client):
    """With the real (test) DB up, readiness should report connected -
    proves the endpoint isn't just hardcoded to say healthy regardless."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"


def test_check_database_connection_detects_real_failure():
    """
    This is the actual correctness proof: point the same check function
    at a deliberately broken database and confirm it reports failure
    rather than silently returning healthy.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import app.core.database as db_module

    broken_engine = create_engine("sqlite:////nonexistent-dir-xyz/broken.db")
    broken_session_local = sessionmaker(bind=broken_engine)

    real_session_local = db_module.SessionLocal
    db_module.SessionLocal = broken_session_local
    try:
        is_connected, error = check_database_connection()
        assert is_connected is False
        assert error is not None
    finally:
        db_module.SessionLocal = real_session_local

    is_connected, error = check_database_connection()
    assert is_connected is True
    assert error is None


def test_login_still_works_within_rate_limit(client, admin_token):
    """Confirms the @limiter.limit decorator on /auth/login didn't break
    normal login - exercised lightly to avoid eating into the shared
    quota other tests' admin_token fixture depends on."""
    resp = client.post("/api/auth/login", json={
        "email": "admin@test.com", "password": "Admin@12345",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_rate_limiter_blocks_after_threshold_isolated():
    """
    Proves the rate-limiting mechanism itself actually blocks excess
    requests, using a throwaway app + Limiter (not the shared one) so
    this can safely use a very low limit without affecting any other test.
    """
    isolated_app = FastAPI()
    isolated_limiter = Limiter(key_func=get_remote_address)
    isolated_app.state.limiter = isolated_limiter
    isolated_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    isolated_app.add_middleware(SlowAPIMiddleware)

    @isolated_app.get("/ping")
    @isolated_limiter.limit("3/minute")
    async def ping(request: Request):
        return {"pong": True}

    test_client = TestClient(isolated_app)

    for _ in range(3):
        resp = test_client.get("/ping")
        assert resp.status_code == 200

    resp = test_client.get("/ping")
    assert resp.status_code == 429
