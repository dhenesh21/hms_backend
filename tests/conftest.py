"""
Shared pytest fixtures.

Uses an isolated in-memory-ish SQLite file (not the real Postgres) so tests
run fast and never touch a real database. This is fine for testing business
logic/response shapes; it does NOT replace verifying migrations against real
Postgres (see backend/alembic).
"""
import os
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "_test.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

# Point the app at the test DB BEFORE importing app modules, since
# app.core.database creates the engine at import time.
os.environ["DATABASE_URL"] = TEST_DB_URL

from app.core.database import Base, get_db  # noqa: E402
from app import models  # noqa: E402
from app.models import blood_bank, diet, referral  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    """
    Bootstrap the first admin user directly via the DB, exactly like
    seed.py does. This is intentional, not a workaround: POST /auth/register
    is an admin-only endpoint (only an existing admin can create new staff
    accounts), so the very first admin can never come from that endpoint -
    it has to be seeded directly, same as production setup.
    """
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    db = TestingSessionLocal()
    try:
        admin = User(
            employee_id="AD0001",
            email="admin@test.com",
            hashed_password=get_password_hash("Admin@12345"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            department="Administration",
            is_active=True,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin@12345",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def tomorrow():
    return (date.today() + timedelta(days=1)).isoformat()
