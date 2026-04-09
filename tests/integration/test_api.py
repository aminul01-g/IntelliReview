import pytest
from fastapi import status


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registering with duplicate username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",  # Already exists
                "email": "another@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"


class TestAnalysisEndpoints:
    """Test analysis endpoints."""
    
    def test_analyze_python_code(self, client, auth_headers, sample_python_code):
        """Test analyzing Python code."""
        response = client.post(
            "/api/v1/analysis/analyze",
            headers=auth_headers,
            json={
                "code": sample_python_code,
                "language": "python",
                "file_path": "test.py"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "analysis_id" in data
        assert data["status"] == "completed"
        assert data["language"] == "python"
        assert "issues" in data
        assert "metrics" in data
    
    def test_analyze_javascript_code(self, client, auth_headers, sample_javascript_code):
        """Test analyzing JavaScript code."""
        response = client.post(
            "/api/v1/analysis/analyze",
            headers=auth_headers,
            json={
                "code": sample_javascript_code,
                "language": "javascript",
                "file_path": "test.js"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["language"] == "javascript"
    
    def test_analyze_unsupported_language(self, client, auth_headers):
        """Test analyzing unsupported language."""
        response = client.post(
            "/api/v1/analysis/analyze",
            headers=auth_headers,
            json={
                "code": "code here",
                "language": "ruby"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_analyze_without_auth(self, client, sample_python_code):
        """Test analyzing without authentication."""
        response = client.post(
            "/api/v1/analysis/analyze",
            json={
                "code": sample_python_code,
                "language": "python"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_analysis_history(self, client, auth_headers):
        """Test getting analysis history."""
        response = client.get(
            "/api/v1/analysis/history",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestMetricsEndpoints:
    """Test metrics endpoints."""
    
    def test_get_user_metrics(self, client, auth_headers):
        """Test getting user metrics."""
        response = client.get(
            "/api/v1/metrics/user",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_analyses" in data
        assert "weekly_analyses" in data
        assert "language_breakdown" in data


class TestFeedbackEndpoints:
    """Test feedback endpoints."""
    
    def test_submit_feedback(self, client, auth_headers):
        """Test submitting feedback."""
        response = client.post(
            "/api/v1/feedback/submit",
            headers=auth_headers,
            json={
                "suggestion_id": "test123",
                "accepted": True,
                "issue_type": "long_method",
                "comment": "Helpful suggestion"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["accepted"] == True
    
    def test_get_feedback_stats(self, client, auth_headers):
        """Test getting feedback statistics."""
        response = client.get(
            "/api/v1/feedback/stats",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "statistics" in data

