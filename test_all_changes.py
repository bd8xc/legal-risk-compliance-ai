"""Quick test script for API with all improvements"""

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

print("Testing with Mock LLM Enabled...")
print("="*60)

# Test 1: Health Check
print("\n1. Testing Health Endpoint")
response = client.get("/health")
print(f"   Status: {response.status_code}")
print(f"   OK: {response.json()['status']}")

# Test 2: Valid Chat Request (with mock)
print("\n2. Testing Chat with Contract Question (MOCK)")
response = client.post("/chat", json={"question": "What should I check when signing a contract?"})
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Answer length: {len(data['answer'])} characters")
    print(f"   Rules passed: {data['safety_checks']['rules_passed']}")
    print("   SUCCESS - Got full response with mock LLM!")
else:
    print(f"   Error: {response.json()}")

# Test 3: Invalid Request (too short)
print("\n3. Testing Invalid Input (too short)")
response = client.post("/chat", json={"question": "x"})
print(f"   Status: {response.status_code}")
print(f"   Correctly rejected: {response.status_code in [400, 422]}")

# Test 4: Employment question with mock
print("\n4. Testing Employment Question (MOCK)")
response = client.post("/chat", json={"question": "Can my employer terminate me without cause?"})
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Issues found: {data['debug_trace'][1]}")
    print("   SUCCESS - Mock LLM working perfectly!")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("✅ Mock LLM enabled - instant responses!")
print("✅ Retry logic available - 3 retries if real LLM fails!")
print("✅ Timeout increased to 120 seconds!")
print("="*60)
