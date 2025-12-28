import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import pytest

# Set dummy environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SMART_API_KEY"] = "test_key"
os.environ["SMART_API_CLIENT_CODE"] = "test_client"
os.environ["SMART_API_PASSWORD"] = "test_password"
os.environ["SMART_API_TOTP_TOKEN"] = "test_token"

from main import app, get_smart_api_handler

# Create a mock handler to be used in tests
mock_handler_instance = MagicMock()

def get_mock_smart_api_handler():
    """Dependency override to return the mock handler."""
    return mock_handler_instance

app.dependency_overrides[get_smart_api_handler] = get_mock_smart_api_handler

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock():
    """Reset the mock before each test."""
    mock_handler_instance.reset_mock()

def test_read_main():
    """Tests the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

def test_get_option_chain_success():
    """Tests the option chain endpoint with a successful API call."""
    mock_option_chain = {
        "calls": [{"symbol": "NIFTY24JUL25000CE", "token": "12345", "strike": 25000, "ltp": 150.25, "iv": 15.5, "oi": 120000}],
        "puts": [{"symbol": "NIFTY24JUL25000PE", "token": "54321", "strike": 25000, "ltp": 85.10, "iv": 16.2, "oi": 110000}]
    }
    mock_tokens = ["12345", "54321"]
    mock_handler_instance.get_option_chain.return_value = (mock_option_chain, mock_tokens)

    response = client.get("/api/option-chain")

    assert response.status_code == 200
    data = response.json()
    assert data["calls"][0]["symbol"] == "NIFTY24JUL25000CE"
    assert data["puts"][0]["symbol"] == "NIFTY24JUL25000PE"
    mock_handler_instance.get_option_chain.assert_called_once_with("NIFTY", "25JUL2024")
    mock_handler_instance.subscribe_to_symbols.assert_called_once_with(mock_tokens)

def test_get_option_chain_api_failure():
    """Tests the option chain endpoint when the API handler returns None."""
    mock_handler_instance.get_option_chain.return_value = (None, [])

    response = client.get("/api/option-chain")

    assert response.status_code == 200
    data = response.json()
    assert data == {"calls": [], "puts": []}
