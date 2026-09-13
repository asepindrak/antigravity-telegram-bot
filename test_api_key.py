import os
from fastapi.testclient import TestClient

# Set environment variable before importing app
os.environ["AGY_BRIDGE_API_KEY"] = "sk-test-key-999"

from openai_agy_bridge import app

client = TestClient(app)

def test_missing_api_key():
    response = client.get("/v1/models")
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]

def test_invalid_api_key():
    # Attempting with random/wrong key (even starting with sk-) must be rejected
    response = client.get("/v1/models", headers={"Authorization": "Bearer sk-random-wrong-key"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

def test_valid_api_key():
    response = client.get("/v1/models", headers={"Authorization": "Bearer sk-test-key-999"})
    assert response.status_code == 200
    assert response.json()["object"] == "list"

def test_root_endpoint_hides_api_key():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["api_key"] != "sk-test-key-999"
    assert "sk-test-key-999" not in data["instructions"]

if __name__ == "__main__":
    test_missing_api_key()
    test_invalid_api_key()
    test_valid_api_key()
    test_root_endpoint_hides_api_key()
    print("All API Key strict validation tests passed successfully!")
