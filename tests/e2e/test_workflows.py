import pytest
from fastapi import status


class TestCompleteWorkflow:
    """Test complete user workflows."""
    
    def test_user_registration_to_analysis(self, client, sample_python_code):
        """Test complete workflow: register → login → analyze."""
        
        # 1. Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "workflow_user",
                "email": "workflow@example.com",
                "password": "password123"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # 2. Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "workflow_user",
                "password": "password123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Analyze code
        analyze_response = client.post(
            "/api/v1/analysis/analyze",
            headers=headers,
            json={
                "code": sample_python_code,
                "language": "python",
                "file_path": "main.py"
            }
        )
        assert analyze_response.status_code == status.HTTP_200_OK
        analysis = analyze_response.json()
        
        # 4. Check metrics
        metrics_response = client.get(
            "/api/v1/metrics/user",
            headers=headers
        )
        assert metrics_response.status_code == status.HTTP_200_OK
        metrics = metrics_response.json()
        assert metrics["total_analyses"] >= 1
        
        # 5. Submit feedback
        feedback_response = client.post(
            "/api/v1/feedback/submit",
            headers=headers,
            json={
                "suggestion_id": f"analysis_{analysis['analysis_id']}",
                "accepted": True,
                "issue_type": "test",
                "comment": "Great analysis!"
            }
        )
        assert feedback_response.status_code == status.HTTP_200_OK

