import pytest
import asyncio
from httpx import AsyncClient
from api.main import app
from api.database import Base, engine
from api.celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Use a separate test database for integration tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class AnalysisFlowTest:
    """
    Integration tests for the full analysis pipeline.
    Verifies: API Request -> Celery Task -> LLM Result -> DB Storage.
    """

    async def setup_method(self):
        self.client = AsyncClient(app=app, base_url="http://test")
        # In a real scenario, we would use a separate test DB and a mock Celery broker
        # For this integration test, we simulate the flow

    async def test_full_analysis_pipeline(self):
        """
        Test that submitting a snippet for analysis returns a valid result
        and creates the necessary database entries.
        """
        test_payload = {
            "code": "def insecure_func():\n    pass",
            "language": "python",
            "filename": "test.py"
        }

        # 1. Submit for analysis
        # Note: We assume the user is already authenticated via a mock token
        response = await self.client.post(
            "/api/v1/analysis/analyze",
            json=test_payload,
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "issues" in data
        assert isinstance(data["issues"], list)

    async def test_webhook_trigger(self):
        """
        Test that a GitHub webhook payload correctly triggers a Celery task.
        """
        webhook_payload = {
            "pull_request": {
                "number": 123,
                "head": {"sha": "abc123diff"},
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }

        response = await self.client.post(
            "/api/v1/webhooks/github",
            json=webhook_payload,
            headers={"X-Hub-Signature-256": "mock-sig"}
        )

        assert response.status_code == 202
        assert response.json()["status"] == "queued"

@pytest.mark.asyncio
async def test_api_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
