"""Integration tests for FastAPI server.

Property 11: API Validates Request Field Lengths
Validates: Requirements 8.3, 8.4
"""

from fastapi.testclient import TestClient
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from api.server import app

client = TestClient(app)


class TestAPIFieldValidation:
    """Test API field length validation."""

    def test_health_returns_ok(self):
        """GET /health should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_chat_valid_request(self):
        """POST /chat with valid body should succeed."""
        response = client.post("/chat", json={
            "session_id": "test-session",
            "question": "Why did the Lambda fail?",
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "cited_log_ids" in data
        assert isinstance(data["cited_log_ids"], list)

    def test_chat_missing_session_id(self):
        """POST /chat without session_id should fail."""
        response = client.post("/chat", json={
            "question": "Why did the Lambda fail?",
        })
        assert response.status_code == 422

    def test_chat_empty_session_id(self):
        """POST /chat with empty session_id should fail."""
        response = client.post("/chat", json={
            "session_id": "",
            "question": "Why did the Lambda fail?",
        })
        assert response.status_code == 422

    def test_chat_missing_question(self):
        """POST /chat without question should fail."""
        response = client.post("/chat", json={
            "session_id": "test-session",
        })
        assert response.status_code == 422

    @given(session_id_len=st.integers(min_value=129, max_value=200))
    @settings(max_examples=10)
    def test_chat_oversized_session_id(self, session_id_len):
        """POST /chat with oversized session_id should fail."""
        response = client.post("/chat", json={
            "session_id": "x" * session_id_len,
            "question": "Why did the Lambda fail?",
        })
        assert response.status_code == 422

    @given(question_len=st.integers(min_value=1001, max_value=1500))
    @settings(max_examples=10)
    def test_chat_oversized_question(self, question_len):
        """POST /chat with oversized question should fail."""
        response = client.post("/chat", json={
            "session_id": "test-session",
            "question": "x" * question_len,
        })
        assert response.status_code == 422
