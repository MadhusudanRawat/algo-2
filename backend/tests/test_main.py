import os
from fastapi.testclient import TestClient

# Set a dummy DATABASE_URL for testing purposes before importing the app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
