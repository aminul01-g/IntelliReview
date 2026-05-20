"""
Integration test: Full Analysis Flow.

Spins up a test SQLite database, registers a user, uploads/analyzes code,
and verifies an Analysis record is created in the database.

Marked with @pytest.mark.integration so CI can run it separately.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.main import app


# ── Test Database Setup ──────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_integration.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Yield a test DB session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests and tear down after."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    # Clean up test DB file
    import os
    try:
        os.remove("./test_integration.db")
    except OSError:
        pass


@pytest.fixture(scope="module")
def client():
    """Create a synchronous test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Register a test user and return auth headers with a valid JWT."""
    # Register
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "integration_test_user",
            "email": "integ@test.com",
            "password": "TestPassword123!",
        },
    )
    assert register_resp.status_code in (200, 201, 409), (
        f"Registration failed: {register_resp.text}"
    )

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "integration_test_user",
            "password": "TestPassword123!",
        },
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"

    token = login_resp.json().get("access_token")
    assert token, "No access_token returned from login"

    return {"Authorization": f"Bearer {token}"}


# ── Integration Tests ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestAnalysisFlow:
    """End-to-end analysis flow: submit code → verify DB record."""

    def test_analyze_code_creates_record(self, client, auth_headers):
        """Submit a snippet for analysis and verify an Analysis row is created."""
        payload = {
            "code": "def foo():\n    eval(input())\n    return 42\n",
            "language": "python",
            "file_path": "test_snippet.py",
        }

        resp = client.post(
            "/api/v1/analysis/analyze",
            json=payload,
            headers=auth_headers,
        )

        assert resp.status_code == 200, f"Analyze failed: {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "analysis_id" in data
        assert "issues" in data
        assert isinstance(data["issues"], list)
        assert data["status"] in ("completed", "SUCCESS")
        assert data["language"] == "python"

        # Verify the record exists in the database
        db = TestingSessionLocal()
        try:
            from api.models.analysis import Analysis

            record = db.query(Analysis).filter(Analysis.id == data["analysis_id"]).first()
            assert record is not None, "Analysis record was not persisted to the database"
            assert record.language == "python"
            assert record.status in ("completed", "SUCCESS")
            assert record.issues is not None
        finally:
            db.close()

    def test_analysis_history_returns_record(self, client, auth_headers):
        """After analysis, the history endpoint should include the result."""
        resp = client.get(
            "/api/v1/analysis/history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        history = resp.json()
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_health_endpoint(self, client):
        """Health endpoint should be publicly accessible."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_metrics_endpoint(self, client):
        """Prometheus metrics should be scrape-able."""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "http_requests_total" in resp.text or "HELP" in resp.text
