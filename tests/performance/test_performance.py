import pytest
import time
from concurrent.futures import ThreadPoolExecutor


class TestPerformance:
    """Performance tests."""
    
    @pytest.mark.slow
    def test_analysis_performance(self, client, auth_headers, sample_python_code):
        """Test analysis performance."""
        
        start_time = time.time()
        
        response = client.post(
            "/api/v1/analysis/analyze",
            headers=auth_headers,
            json={
                "code": sample_python_code,
                "language": "python"
            }
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code == 200
        assert duration < 5.0  # Should complete in under 5 seconds
    
    @pytest.mark.slow
    def test_concurrent_requests(self, client, auth_headers, sample_python_code):
        """Test handling concurrent requests."""
        
        def make_request():
            return client.post(
                "/api/v1/analysis/analyze",
                headers=auth_headers,
                json={
                    "code": sample_python_code,
                    "language": "python"
                }
            )
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in results)