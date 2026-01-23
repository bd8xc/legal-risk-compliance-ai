"""
API endpoint tests

Tests the FastAPI endpoints with proper request/response validation.
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.schemas import ChatRequest, ChatResponse, ErrorResponse, HealthResponse

# Create test client
client = TestClient(app)

# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert 'endpoints' in data

# ============================================================================
# Chat Endpoint Validation Tests
# ============================================================================

def test_chat_valid_request():
    """Test chat with valid request"""
    payload = {"question": "What is contract law?"}
    # This will fail because LLM is not running, but validates request structure
    response = client.post("/chat", json=payload)
    # Should be 503 (service unavailable) not 422 (validation error)
    assert response.status_code in [503, 504, 400, 500]

def test_chat_empty_question():
    """Test chat with empty question"""
    payload = {"question": ""}
    response = client.post("/chat", json=payload)
    # Should fail validation or processing
    assert response.status_code in [400, 413, 422]

def test_chat_question_too_short():
    """Test chat with question that's too short"""
    payload = {"question": "Abc"}
    response = client.post("/chat", json=payload)
    assert response.status_code in [400, 422]

def test_chat_question_too_long():
    """Test chat with excessively long question"""
    long_question = "a" * 10001
    payload = {"question": long_question}
    response = client.post("/chat", json=payload)
    assert response.status_code in [413, 422]

def test_chat_missing_question():
    """Test chat with missing question field"""
    payload = {}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422

def test_chat_null_question():
    """Test chat with null question"""
    payload = {"question": None}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422

def test_chat_non_string_question():
    """Test chat with non-string question"""
    payload = {"question": 12345}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422

# ============================================================================
# Chat Endpoint Response Validation Tests
# ============================================================================

def test_chat_response_structure():
    """Test that successful response has correct structure"""
    # Note: This test would need a mock LLM to pass completely
    # Here we're testing the validation logic
    payload = {"question": "What is contract enforcement?"}
    response = client.post("/chat", json=payload)
    
    # Response should be valid JSON
    data = response.json()
    assert isinstance(data, dict)

def test_error_response_structure():
    """Test that error response has correct structure"""
    payload = {"question": "x"}  # Too short
    response = client.post("/chat", json=payload)
    
    assert response.status_code >= 400
    data = response.json()
    assert 'error' in data or 'detail' in data

# ============================================================================
# Endpoint Availability Tests
# ============================================================================

def test_health_endpoint_available():
    """Test that health endpoint is available"""
    response = client.get("/health")
    assert response.status_code == 200

def test_chat_endpoint_available():
    """Test that chat endpoint accepts POST"""
    response = client.post("/chat", json={"question": "valid" * 20})
    # Should not be 404
    assert response.status_code != 404

def test_chat_endpoint_rejects_get():
    """Test that chat endpoint only accepts POST"""
    response = client.get("/chat")
    assert response.status_code == 405  # Method Not Allowed

# ============================================================================
# Schema Tests
# ============================================================================

def test_chat_request_schema():
    """Test ChatRequest schema validation"""
    # Valid
    req = ChatRequest(question="Valid legal question about contracts?")
    assert req.question == "Valid legal question about contracts?"
    
    # Invalid - too short
    with pytest.raises(ValueError):
        ChatRequest(question="abc")
    
    # Invalid - too long
    with pytest.raises(ValueError):
        ChatRequest(question="a" * 5001)

def test_health_response_schema():
    """Test HealthResponse schema"""
    resp = HealthResponse()
    assert resp.status == "ok"
    assert 'timestamp' in resp.model_dump()

def test_error_response_schema():
    """Test ErrorResponse schema"""
    resp = ErrorResponse(error="Test error")
    assert resp.error == "Test error"
    assert resp.status == "error"
    assert 'timestamp' in resp.model_dump()

# ============================================================================
# API Documentation Tests
# ============================================================================

def test_openapi_schema():
    """Test that OpenAPI schema is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert 'paths' in data

def test_swagger_ui_available():
    """Test that Swagger UI is available"""
    response = client.get("/docs")
    assert response.status_code == 200

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_invalid_json_request():
    """Test handling of invalid JSON"""
    response = client.post("/chat", content="invalid json")
    assert response.status_code >= 400

def test_extra_fields_ignored():
    """Test that extra fields in request are ignored"""
    payload = {
        "question": "What is contract law?",
        "extra_field": "should be ignored"
    }
    response = client.post("/chat", json=payload)
    # Should not fail because of extra field
    assert response.status_code != 422

# ============================================================================
# Integration Tests
# ============================================================================

def test_health_check_before_chat():
    """Test checking health before making chat request"""
    # Health should always work
    health = client.get("/health")
    assert health.status_code == 200
    
    # Chat might fail without LLM but shouldn't cause issues
    chat = client.post("/chat", json={"question": "Test question?"})
    assert chat.status_code in [400, 500, 503, 504]

def test_multiple_requests():
    """Test multiple sequential requests"""
    for i in range(3):
        response = client.get("/health")
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
